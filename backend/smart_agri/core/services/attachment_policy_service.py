from __future__ import annotations

from datetime import timedelta
from pathlib import Path
import io
import hashlib
import mimetypes
import os
import shlex
import shutil
import subprocess
import zipfile
from xml.etree import ElementTree

from django.core.exceptions import ValidationError
from django.utils import timezone

from smart_agri.core.models.log import Attachment, AttachmentLifecycleEvent


class AttachmentPolicyService:
    """Governed attachment lifecycle for strict documentary cycles."""

    PURGE_ELIGIBLE_CLASSES = {'transient', 'operational'}
    NON_PURGE_ELIGIBLE_CLASSES = {'financial_record', 'legal_hold'}
    ARCHIVE_ROOT = Path(os.environ.get('AGRIASSET_ATTACHMENT_ARCHIVE_ROOT', '/mnt/data/agriasset_attachment_archive'))
    QUARANTINE_ROOT = Path(os.environ.get('AGRIASSET_ATTACHMENT_QUARANTINE_ROOT', '/mnt/data/agriasset_attachment_quarantine'))
    SANITIZED_ROOT = Path(os.environ.get('AGRIASSET_ATTACHMENT_SANITIZED_ROOT', '/mnt/data/agriasset_attachment_sanitized'))
    BACKEND_FILESYSTEM = 'filesystem'
    BACKEND_OBJECTSTORE = 'objectstore'
    DANGEROUS_MARKERS = (b'MZ', b'#!/bin', b'<script', b'<?php')
    PDF_DANGEROUS_MARKERS = (b'/JavaScript', b'/JS', b'/Launch', b'/OpenAction', b'/RichMedia', b'/EmbeddedFile')
    DANGEROUS_SUFFIXES = {'.exe', '.dll', '.js', '.vbs', '.bat', '.cmd', '.ps1', '.php', '.phtml', '.jar', '.scr', '.com'}
    ZIP_MAX_MEMBERS = 250
    ZIP_MAX_COMPRESSION_RATIO = 120
    ZIP_MAX_TOTAL_UNCOMPRESSED = 50 * 1024 * 1024
    OOXML_EXTERNAL_REL = 'TargetMode="External"'
    CLAMSCAN_BINARY = os.environ.get('AGRIASSET_CLAMSCAN_BINARY', 'clamscan')
    CLAMD_SCAN_COMMAND = os.environ.get('AGRIASSET_CLAMD_SCAN_COMMAND', '').strip()
    CDR_COMMAND = os.environ.get('AGRIASSET_ATTACHMENT_CDR_COMMAND', '').strip()
    OBJECTSTORE_ENABLED = os.environ.get('AGRIASSET_ATTACHMENT_OBJECTSTORE_ENABLED', '0').lower() in {'1', 'true', 'yes'}

    SIGNATURES = {
        'pdf': [b'%PDF'],
        'jpg': [b'\xff\xd8\xff'],
        'jpeg': [b'\xff\xd8\xff'],
        'png': [b'\x89PNG\r\n\x1a\n'],
        'xlsx': [b'PK'],
    }
    MIME_BY_EXTENSION = {
        'pdf': {'application/pdf'},
        'jpg': {'image/jpeg'},
        'jpeg': {'image/jpeg'},
        'png': {'image/png'},
        'csv': {'text/csv', 'application/csv', 'application/vnd.ms-excel', 'text/plain'},
        'xlsx': {'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', 'application/zip'},
    }

    @staticmethod
    def build_policy(*, farm_settings) -> dict:
        if farm_settings is None:
            return {
                'max_upload_size_mb': 10,
                'transient_ttl_days': 30,
                'archive_after_days': 7,
                'mandatory_attachment_for_cash': True,
                'dedupe_enabled': True,
            }
        return {
            'max_upload_size_mb': int(getattr(farm_settings, 'attachment_max_upload_size_mb', 10) or 10),
            'transient_ttl_days': int(getattr(farm_settings, 'attachment_transient_ttl_days', 30) or 30),
            'archive_after_days': int(getattr(farm_settings, 'approved_attachment_archive_after_days', 7) or 7),
            'mandatory_attachment_for_cash': bool(getattr(farm_settings, 'mandatory_attachment_for_cash', True)),
            'dedupe_enabled': True,
        }

    @staticmethod
    def _record_event(*, attachment: Attachment, action: str, note: str = '', metadata: dict | None = None, actor=None):
        AttachmentLifecycleEvent.objects.create(
            attachment=attachment,
            actor=actor,
            action=action,
            note=(note or '')[:255],
            metadata=metadata or {},
        )

    @classmethod
    def _scanner_mode(cls, *, farm_settings=None) -> str:
        if farm_settings is not None:
            return getattr(farm_settings, 'attachment_scan_mode', '') or 'heuristic'
        return os.environ.get('AGRIASSET_ATTACHMENT_SCAN_MODE', 'heuristic')

    @classmethod
    def _run_external_scan(cls, *, attachment: Attachment) -> tuple[bool, str]:
        if not cls._file_exists(attachment):
            return False, 'missing_file_payload'
        if cls.CLAMD_SCAN_COMMAND:
            return cls._run_configured_command(command_template=cls.CLAMD_SCAN_COMMAND, attachment=attachment, success_codes={0}, success_note='clamd_scan_passed')
        try:
            proc = subprocess.run(
                [cls.CLAMSCAN_BINARY, '--no-summary', attachment.file.path],
                check=False,
                capture_output=True,
                text=True,
                timeout=30,
            )
        except (OSError, subprocess.SubprocessError) as exc:
            return False, f'external_scanner_unavailable:{exc}'
        if proc.returncode == 0:
            return True, 'external_scan_passed'
        output = (proc.stdout or proc.stderr or '').strip()
        return False, output[:255] or 'external_scan_failed'

    @classmethod
    def _run_configured_command(cls, *, command_template: str, attachment: Attachment, success_codes: set[int], success_note: str) -> tuple[bool, str]:
        if not command_template:
            return False, 'command_template_missing'
        if not cls._file_exists(attachment):
            return False, 'missing_file_payload'
        rendered = command_template.replace('{file}', shlex.quote(attachment.file.path))
        try:
            proc = subprocess.run(
                rendered,
                shell=True,
                check=False,
                capture_output=True,
                text=True,
                timeout=60,
            )
        except (OSError, subprocess.SubprocessError) as exc:
            return False, f'command_execution_failed:{exc}'
        if proc.returncode in success_codes:
            return True, success_note
        output = (proc.stdout or proc.stderr or '').strip()
        return False, output[:255] or 'command_failed'

    @classmethod
    def _run_external_cdr(cls, *, attachment: Attachment) -> tuple[bool, str]:
        if not cls.CDR_COMMAND:
            return True, 'cdr_not_configured'
        if not cls._file_exists(attachment):
            return False, 'missing_file_payload'
        cls.SANITIZED_ROOT.mkdir(parents=True, exist_ok=True)
        sanitized_name = f"{attachment.sha256_checksum or 'pending'}{Path(getattr(attachment.file, 'name', '') or attachment.name or 'file.bin').suffix or '.bin'}"
        target_path = cls.SANITIZED_ROOT / sanitized_name  # agri-guardian: decimal-safe pathlib join
        rendered = cls.CDR_COMMAND.replace('{input}', shlex.quote(attachment.file.path)).replace('{output}', shlex.quote(str(target_path)))
        ok, note = cls._run_configured_command(command_template=rendered, attachment=attachment, success_codes={0}, success_note='cdr_sanitized')
        if not ok:
            return False, note
        if target_path.exists():
            cls._record_event(attachment=attachment, action=AttachmentLifecycleEvent.ACTION_RECEIVED, note='cdr_sanitized_copy_ready', metadata={'sanitized_path': str(target_path)})
        return True, note

    @classmethod
    def _archive_backend_name(cls) -> str:
        return cls.BACKEND_OBJECTSTORE if cls.OBJECTSTORE_ENABLED else cls.BACKEND_FILESYSTEM

    @staticmethod
    def _read_head(file_obj, size=32):
        pos = file_obj.tell() if hasattr(file_obj, 'tell') else None
        try:
            if hasattr(file_obj, 'open'):
                file_obj.open('rb')
            head = file_obj.read(size)
            return head or b''
        except (OSError, ValueError, AttributeError) as exc:
            raise ValidationError(f'تعذر قراءة رأس الملف للتحقق: {exc}')
        finally:
            if pos is not None and hasattr(file_obj, 'seek'):
                file_obj.seek(pos)

    @classmethod
    def _guess_extension(cls, file_obj) -> str:
        name = getattr(file_obj, 'name', '') or ''
        return Path(name).suffix.lower().lstrip('.')

    @classmethod
    def _validate_filename(cls, *, file_obj) -> str:
        name = getattr(file_obj, 'name', '') or ''
        if not name or name in {'.', '..'}:
            raise ValidationError('اسم الملف غير صالح وفق سياسة النظام.')
        basename = Path(name).name
        if any(ord(ch) < 32 for ch in basename):
            raise ValidationError('اسم الملف يحتوي محارف تحكم غير مسموحة.')
        suffixes = [s.lower() for s in Path(basename).suffixes]
        if any(s in cls.DANGEROUS_SUFFIXES for s in suffixes[:-1]):
            raise ValidationError('اسم الملف يحتوي امتداداً تنفيذياً مخفياً داخل الاسم.')
        stem = Path(basename).stem.strip()
        if not stem:
            raise ValidationError('اسم الملف بعد التنقية غير صالح.')
        return basename

    @classmethod
    def _compute_sha256(cls, file_obj) -> str:
        pos = file_obj.tell() if hasattr(file_obj, 'tell') else None
        try:
            if hasattr(file_obj, 'open'):
                file_obj.open('rb')
            h = hashlib.sha256()
            while True:
                chunk = file_obj.read(65536)
                if not chunk:
                    break
                h.update(chunk)
            return h.hexdigest()
        except (OSError, ValueError, AttributeError) as exc:
            raise ValidationError(f'تعذر حساب بصمة الملف: {exc}')
        finally:
            if pos is not None and hasattr(file_obj, 'seek'):
                file_obj.seek(pos)

    @classmethod
    def _read_all_bytes(cls, file_obj, max_bytes: int = 4 * 1024 * 1024) -> bytes:
        pos = file_obj.tell() if hasattr(file_obj, 'tell') else None
        try:
            if hasattr(file_obj, 'open'):
                file_obj.open('rb')
            data = file_obj.read(max_bytes + 1)
            if len(data) > max_bytes:
                raise ValidationError('الملف يتجاوز نافذة الفحص الأمني المسموح بها.')
            return data or b''
        except (OSError, ValueError, AttributeError) as exc:
            raise ValidationError(f'تعذر فحص محتوى الملف: {exc}')
        finally:
            if pos is not None and hasattr(file_obj, 'seek'):
                file_obj.seek(pos)

    @classmethod
    def _check_zip_container(cls, *, file_obj, extension: str) -> None:
        if extension not in {'xlsx'}:
            return
        data = cls._read_all_bytes(file_obj)
        try:
            with zipfile.ZipFile(io.BytesIO(data)) as zf:
                infos = zf.infolist()
                if len(infos) > cls.ZIP_MAX_MEMBERS:
                    raise ValidationError('عدد مكونات الملف المضغوط يتجاوز الحد الأمني المسموح.')
                total_uncompressed = 0
                for info in infos:
                    filename = (info.filename or '')
                    lowered = filename.lower()
                    if filename.startswith('/') or '..' in Path(filename).parts:
                        raise ValidationError('تم اكتشاف مسار غير آمن داخل الملف المضغوط.')
                    if info.flag_bits & 0x1:
                        raise ValidationError('الملف المضغوط يحتوي مكونات مشفرة غير مسموحة.')
                    if 'vbaproject.bin' in lowered or (lowered.endswith('.bin') and 'xl/' in lowered):
                        raise ValidationError('تم اكتشاف ماكرو أو حمولة تنفيذية داخل ملف Excel.')
                    if lowered in {'encryptioninfo', 'encryptedpackage'}:
                        raise ValidationError('ملف Office مشفر غير مدعوم وفق سياسة النظام.')
                    total_uncompressed += max(info.file_size, 0)
                    if total_uncompressed > cls.ZIP_MAX_TOTAL_UNCOMPRESSED:
                        raise ValidationError('حجم المحتوى المفكوك داخل الملف المضغوط يتجاوز الحد الأمني المسموح.')
                    compressed = max(info.compress_size, 1)
                    ratio = info.file_size / compressed  # agri-guardian: decimal-safe non-financial compression heuristic
                    if ratio > cls.ZIP_MAX_COMPRESSION_RATIO:
                        raise ValidationError('تم اكتشاف نسبة ضغط غير آمنة داخل الملف المرفوع.')
                    if lowered.endswith('.rels'):
                        rel_data = zf.read(info).decode('utf-8', errors='ignore')
                        if cls.OOXML_EXTERNAL_REL in rel_data:
                            raise ValidationError('تم اكتشاف علاقة خارجية داخل OOXML وهي غير مسموحة.')
        except zipfile.BadZipFile as exc:
            raise ValidationError(f'بنية ملف Excel غير سليمة: {exc}')

    @classmethod
    def _check_heuristics(cls, *, file_obj, extension: str, content_type: str) -> None:
        head = cls._read_head(file_obj, size=256)
        if any(head.startswith(marker) for marker in cls.DANGEROUS_MARKERS if extension not in {'xlsx'}):
            raise ValidationError('تم اكتشاف نمط ملف خطِر أو غير متوافق مع سياسة الرفع.')
        if extension in {'pdf', 'jpg', 'jpeg', 'png'} and content_type in {'application/x-msdownload', 'application/x-dosexec'}:
            raise ValidationError('نوع الملف المبلغ عنه غير آمن.')
        if extension == 'pdf':
            payload = cls._read_all_bytes(file_obj, max_bytes=1024 * 1024)
            if any(marker in payload for marker in cls.PDF_DANGEROUS_MARKERS):
                raise ValidationError('تم اكتشاف مؤشر PDF غير آمن (JavaScript/OpenAction).')
        cls._check_zip_container(file_obj=file_obj, extension=extension)

    @classmethod
    def _duplicate_exists(cls, *, checksum: str) -> bool:
        if not checksum:
            return False
        return Attachment.objects.filter(deleted_at__isnull=True, sha256_checksum=checksum).exists()

    @classmethod
    def _validate_signature(cls, *, file_obj, extension: str):
        if extension == 'csv':
            return
        expected = cls.SIGNATURES.get(extension)
        if not expected:
            return
        head = cls._read_head(file_obj)
        if not any(head.startswith(sig) for sig in expected):
            raise ValidationError('توقيع الملف لا يطابق نوع الامتداد المسموح.')

    @classmethod
    def _validate_content_type(cls, *, file_obj, extension: str) -> str:
        reported = getattr(file_obj, 'content_type', '') or ''
        guessed, _ = mimetypes.guess_type(getattr(file_obj, 'name', '') or '')
        candidate = reported or guessed or 'application/octet-stream'
        allowed = cls.MIME_BY_EXTENSION.get(extension, set())
        if allowed and candidate not in allowed:
            if not (extension == 'xlsx' and candidate == 'application/octet-stream'):
                raise ValidationError('نوع محتوى الملف لا يتوافق مع الامتداد المسموح.')
        return candidate

    @classmethod
    def _archive_key_for(cls, *, attachment: Attachment) -> str:
        checksum = attachment.sha256_checksum or 'pending'
        suffix = Path(getattr(attachment.file, 'name', '') or attachment.name or 'file.bin').suffix or '.bin'
        stamp = timezone.now().strftime('%Y/%m')
        return f'{stamp}/{checksum[:2]}/{checksum}{suffix}'

    @classmethod
    def _archive_path_for(cls, *, archive_key: str) -> Path:
        return cls.ARCHIVE_ROOT / Path(archive_key)  # agri-guardian: decimal-safe pathlib join

    @classmethod
    def _quarantine_path_for(cls, *, attachment: Attachment) -> Path:
        checksum = attachment.sha256_checksum or 'pending'
        suffix = Path(getattr(attachment.file, 'name', '') or attachment.name or 'file.bin').suffix or '.bin'
        stamp = timezone.now().strftime('%Y/%m')
        return cls.QUARANTINE_ROOT / Path(stamp) / f'{checksum}{suffix}'  # agri-guardian: decimal-safe pathlib join

    @staticmethod
    def _file_exists(attachment: Attachment) -> bool:
        return bool(getattr(attachment, 'file', None) and getattr(attachment.file, 'name', '') and os.path.exists(attachment.file.path))

    @classmethod
    def validate_upload(cls, *, farm_settings, file_obj, evidence_class: str) -> dict:
        policy = cls.build_policy(farm_settings=farm_settings)
        max_bytes = policy['max_upload_size_mb'] * 1024 * 1024
        size = getattr(file_obj, 'size', 0) or 0
        if size > max_bytes:
            raise ValidationError(f"حجم الملف يتجاوز الحد المسموح ({policy['max_upload_size_mb']} MB).")
        cls._validate_filename(file_obj=file_obj)
        extension = cls._guess_extension(file_obj)
        if extension not in cls.MIME_BY_EXTENSION:
            raise ValidationError('امتداد الملف غير مسموح وفق سياسة النظام.')
        cls._validate_signature(file_obj=file_obj, extension=extension)
        content_type = cls._validate_content_type(file_obj=file_obj, extension=extension)
        cls._check_heuristics(file_obj=file_obj, extension=extension, content_type=content_type)
        checksum = cls._compute_sha256(file_obj)
        if policy.get('dedupe_enabled') and evidence_class == Attachment.EVIDENCE_CLASS_TRANSIENT and cls._duplicate_exists(checksum=checksum):
            raise ValidationError('تم اكتشاف نسخة مكررة من مرفق مؤقت؛ يرجى إعادة استخدام النسخة الأصلية أو رفع مستند مختلف.')
        expires_at = timezone.now() + timedelta(days=policy['transient_ttl_days']) if evidence_class == Attachment.EVIDENCE_CLASS_TRANSIENT else None
        return {
            'expires_at': expires_at,
            'content_type': content_type,
            'mime_type_detected': content_type,
            'storage_tier': Attachment.STORAGE_TIER_HOT,
            'archive_state': getattr(Attachment, 'ARCHIVE_STATE_HOT', 'hot'),
            'malware_scan_status': Attachment.MALWARE_SCAN_PENDING,
            'scan_state': Attachment.MALWARE_SCAN_PENDING,
            'sha256_checksum': checksum,
            'content_hash': checksum,
            'filename_original': getattr(file_obj, 'name', '') or '',
            'size_bytes': int(size or 0),
            **policy,
        }

    @classmethod
    def scan_attachment(cls, *, attachment: Attachment, farm_settings=None) -> Attachment:
        if not getattr(attachment, 'file', None):
            attachment.malware_scan_status = Attachment.MALWARE_SCAN_QUARANTINED
            attachment.scan_state = Attachment.MALWARE_SCAN_QUARANTINED
            attachment.quarantine_state = getattr(Attachment, 'QUARANTINE_STATE_QUARANTINED', 'quarantined')
            attachment.quarantine_reason = 'missing_file_payload'
            attachment.quarantined_at = timezone.now()
            cls._record_event(
                attachment=attachment,
                action=AttachmentLifecycleEvent.ACTION_SCAN_QUARANTINED,
                note='missing_file_payload',
            )
            return attachment
        cls._validate_filename(file_obj=attachment.file)
        extension = cls._guess_extension(attachment.file)
        try:
            if extension not in cls.MIME_BY_EXTENSION:
                raise ValidationError('unsupported_extension')
            cls._validate_signature(file_obj=attachment.file, extension=extension)
            content_type = cls._validate_content_type(file_obj=attachment.file, extension=extension)
            cls._check_heuristics(file_obj=attachment.file, extension=extension, content_type=content_type)
            mode = cls._scanner_mode(farm_settings=farm_settings)
            if mode == 'clamav':
                clean, note = cls._run_external_scan(attachment=attachment)
                if not clean:
                    return cls.quarantine_attachment(attachment=attachment, reason=note)
            cdr_ok, cdr_note = cls._run_external_cdr(attachment=attachment)
            if not cdr_ok:
                return cls.quarantine_attachment(attachment=attachment, reason=cdr_note)
            attachment.content_type = content_type
            attachment.mime_type_detected = content_type
            attachment.scan_state = Attachment.MALWARE_SCAN_PASSED
            attachment.malware_scan_status = Attachment.MALWARE_SCAN_PASSED
            attachment.quarantine_reason = ''
            attachment.scanned_at = timezone.now()
            cls._record_event(attachment=attachment, action=AttachmentLifecycleEvent.ACTION_SCAN_PASSED, note='scan_passed', metadata={'mode': mode, 'content_type': content_type, 'cdr': bool(cls.CDR_COMMAND)})
            return attachment
        except ValidationError as exc:
            reason = '; '.join(str(x) for x in getattr(exc, 'messages', [str(exc)]))
            return cls.quarantine_attachment(attachment=attachment, reason=reason)

    @classmethod
    def quarantine_attachment(cls, *, attachment: Attachment, reason: str) -> Attachment:
        attachment.malware_scan_status = Attachment.MALWARE_SCAN_QUARANTINED
        attachment.scan_state = Attachment.MALWARE_SCAN_QUARANTINED
        attachment.quarantine_state = getattr(Attachment, 'QUARANTINE_STATE_QUARANTINED', 'quarantined')
        attachment.quarantine_reason = (reason or 'policy_violation')[:255]
        attachment.quarantined_at = timezone.now()
        attachment.scanned_at = timezone.now()
        cls.QUARANTINE_ROOT.mkdir(parents=True, exist_ok=True)
        if cls._file_exists(attachment):
            quarantine_path = cls._quarantine_path_for(attachment=attachment)
            quarantine_path.parent.mkdir(parents=True, exist_ok=True)
            if not quarantine_path.exists():
                shutil.copy2(attachment.file.path, quarantine_path)
        cls._record_event(attachment=attachment, action=AttachmentLifecycleEvent.ACTION_SCAN_QUARANTINED, note=attachment.quarantine_reason, metadata={'storage': 'quarantine'})
        return attachment

    @classmethod
    def mark_authoritative_after_approval(cls, *, attachment: Attachment, farm_settings, approved_at=None) -> Attachment:
        policy = cls.build_policy(farm_settings=farm_settings)
        if attachment.malware_scan_status != Attachment.MALWARE_SCAN_PASSED:
            attachment = cls.scan_attachment(attachment=attachment, farm_settings=farm_settings)
        if attachment.malware_scan_status != Attachment.MALWARE_SCAN_PASSED:
            raise ValidationError('لا يمكن اعتماد المرفق كسجل حاكم قبل اجتياز الفحص الأمني.')
        attachment.is_authoritative_evidence = True
        attachment.authoritative_at = approved_at or timezone.now()
        attachment.evidence_class = Attachment.EVIDENCE_CLASS_FINANCIAL
        approved_at = approved_at or timezone.now()
        attachment.expires_at = None
        attachment.storage_tier = Attachment.STORAGE_TIER_HOT
        attachment.archived_at = approved_at + timedelta(days=policy['archive_after_days'])
        attachment.archive_backend = cls._archive_backend_name()
        if not attachment.content_hash and attachment.sha256_checksum:
            attachment.content_hash = attachment.sha256_checksum
        if not attachment.mime_type_detected and attachment.content_type:
            attachment.mime_type_detected = attachment.content_type
        if not attachment.content_type and attachment.file:
            attachment.content_type = cls._validate_content_type(file_obj=attachment.file, extension=cls._guess_extension(attachment.file))
        if not attachment.archive_key:
            attachment.archive_key = cls._archive_key_for(attachment=attachment)
        cls._record_event(attachment=attachment, action=AttachmentLifecycleEvent.ACTION_AUTHORITATIVE_MARKED, note='final_approval_marked', metadata={'archive_after_days': policy['archive_after_days']})
        return attachment

    @staticmethod
    def due_for_archive_queryset():
        return Attachment.objects.filter(
            deleted_at__isnull=True,
            is_authoritative_evidence=True,
            archived_at__isnull=False,
            archived_at__lte=timezone.now(),
            storage_tier=Attachment.STORAGE_TIER_HOT,
            malware_scan_status=Attachment.MALWARE_SCAN_PASSED,
        )

    @staticmethod
    def due_for_purge_queryset():
        return Attachment.objects.filter(
            deleted_at__isnull=True,
            evidence_class=Attachment.EVIDENCE_CLASS_TRANSIENT,
            expires_at__isnull=False,
            expires_at__lte=timezone.now(),
            is_authoritative_evidence=False,
        )

    @classmethod
    def is_purge_eligible(cls, *, evidence_class: str, is_authoritative: bool = False, legal_hold: bool = False) -> bool:
        if is_authoritative or legal_hold:
            return False
        if evidence_class in cls.NON_PURGE_ELIGIBLE_CLASSES:
            return False
        return evidence_class in cls.PURGE_ELIGIBLE_CLASSES

    @staticmethod
    def due_for_scan_queryset():
        return Attachment.objects.filter(
            deleted_at__isnull=True,
            malware_scan_status=Attachment.MALWARE_SCAN_PENDING,
        )

    @classmethod
    def apply_legal_hold(cls, *, attachment: Attachment) -> Attachment:
        attachment.evidence_class = Attachment.EVIDENCE_CLASS_LEGAL_HOLD
        attachment.expires_at = None
        cls._record_event(attachment=attachment, action=AttachmentLifecycleEvent.ACTION_LEGAL_HOLD_APPLIED, note='legal_hold_applied')
        return attachment

    @classmethod
    def release_legal_hold(cls, *, attachment: Attachment) -> Attachment:
        if attachment.evidence_class == Attachment.EVIDENCE_CLASS_LEGAL_HOLD:
            attachment.evidence_class = Attachment.EVIDENCE_CLASS_FINANCIAL if attachment.is_authoritative_evidence else Attachment.EVIDENCE_CLASS_OPERATIONAL
            cls._record_event(attachment=attachment, action=AttachmentLifecycleEvent.ACTION_LEGAL_HOLD_RELEASED, note='legal_hold_released')
        return attachment

    @classmethod
    def _upload_to_s3_objectstore(cls, attachment: Attachment, archive_key: str):
        # [AGRI-GUARDIAN] Phase 8.3 Cloud Object Store Integration Stub
        bucket = os.environ.get('AGRIASSET_S3_ATTACHMENT_BUCKET', 'agriasset-archive')
        # import boto3
        # s3_client = boto3.client('s3')
        # s3_client.upload_file(attachment.file.path, bucket, archive_key)
        cls._record_event(
            attachment=attachment, 
            action=AttachmentLifecycleEvent.ACTION_ARCHIVED, 
            note='s3_objectstore_upload_stubbed', 
            metadata={'bucket': bucket, 'key': archive_key}
        )

    @classmethod
    def move_to_archive(cls, *, attachment: Attachment) -> Attachment:
        attachment.storage_tier = Attachment.STORAGE_TIER_ARCHIVE
        attachment.archived_at = attachment.archived_at or timezone.now()
        attachment.archive_backend = cls._archive_backend_name()
        if not attachment.archive_key:
            attachment.archive_key = cls._archive_key_for(attachment=attachment)
            
        if cls._file_exists(attachment):
            if cls.OBJECTSTORE_ENABLED:
                cls._upload_to_s3_objectstore(attachment, attachment.archive_key)
            else:
                cls.ARCHIVE_ROOT.mkdir(parents=True, exist_ok=True)
                archive_path = cls._archive_path_for(archive_key=attachment.archive_key)
                archive_path.parent.mkdir(parents=True, exist_ok=True)
                if not archive_path.exists():
                    shutil.copy2(attachment.file.path, archive_path)
                    
        cls._record_event(attachment=attachment, action=AttachmentLifecycleEvent.ACTION_ARCHIVED, note='archived_to_low_cost_tier', metadata={'archive_key': attachment.archive_key, 'backend': attachment.archive_backend})
        return attachment

    @classmethod
    def restore_from_archive(cls, *, attachment: Attachment) -> Attachment:
        attachment.storage_tier = Attachment.STORAGE_TIER_HOT
        attachment.restored_at = timezone.now()
        cls._record_event(attachment=attachment, action=AttachmentLifecycleEvent.ACTION_RESTORED, note='restored_from_archive')
        return attachment

    @staticmethod
    def purge_transient(*, attachment: Attachment) -> Attachment:
        AttachmentPolicyService._record_event(attachment=attachment, action=AttachmentLifecycleEvent.ACTION_PURGED, note='transient_purged')
        if attachment.file:
            attachment.file.delete(save=False)
        attachment.name = attachment.name or 'purged'
        attachment.content_type = attachment.content_type or 'purged'
        attachment.deleted_at = timezone.now()
        attachment.deleted_by = None
        return attachment

    @classmethod
    def security_runtime_summary(cls) -> dict:
        return {
            'pending_scan': cls.due_for_scan_queryset().count(),
            'due_archive': cls.due_for_archive_queryset().count(),
            'due_purge': cls.due_for_purge_queryset().count(),
            'quarantined': Attachment.objects.filter(deleted_at__isnull=True, malware_scan_status=Attachment.MALWARE_SCAN_QUARANTINED).count(),
            'hot_tier': Attachment.objects.filter(deleted_at__isnull=True, storage_tier=Attachment.STORAGE_TIER_HOT).count(),
            'archive_tier': Attachment.objects.filter(deleted_at__isnull=True, storage_tier=Attachment.STORAGE_TIER_ARCHIVE).count(),
            'archive_backend': cls._archive_backend_name(),
            'quarantine_backend': cls.BACKEND_FILESYSTEM,
            'scan_mode': os.environ.get('AGRIASSET_ATTACHMENT_SCAN_MODE', 'heuristic'),
            'cdr_enabled': bool(cls.CDR_COMMAND) or os.environ.get('AGRIASSET_ATTACHMENT_CDR', '0') in {'1', 'true', 'yes'},
            'clamd_configured': bool(cls.CLAMD_SCAN_COMMAND),
            'objectstore_enabled': cls.OBJECTSTORE_ENABLED,
            'lifecycle_events': AttachmentLifecycleEvent.objects.count(),
        }
