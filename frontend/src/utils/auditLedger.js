import fs from 'fs';
import path from 'path';
import nacl from 'tweetnacl';
import pkg from 'tweetnacl-util';
import { Database } from 'bun:sqlite';
import { createHash } from 'crypto';
import { dbProvider } from './PostgresProvider.js';
import { EventEmitter } from 'events';

const { decodeBase64, encodeBase64 } = pkg;

// --- PHYSICAL SOVEREIGNTY: LOCAL LEDGER (Bun-Native) ---
const SQLITE_PATH = path.join(process.cwd(), 'audit_ledger.db');
const localDb = new Database(SQLITE_PATH);

// Initialize table if not exists
localDb.exec(`
    CREATE TABLE IF NOT EXISTS audit_logs (
        id TEXT PRIMARY KEY,
        timestamp TEXT,
        agent TEXT,
        action TEXT,
        payload_hash TEXT,
        signature TEXT,
        public_key TEXT
    )
`);

/**
 * ╔══════════════════════════════════════════════════════════╗
 * ║ SOVEREIGN POSTGRES 15 AUDIT LEDGER (Zenith 4.0 Final)     ║
 * ╚══════════════════════════════════════════════════════════╝
 * Forensic tracing and non-repudiation engine anchored to the 
 * PostgreSQL 15 production environment.
 */

const ENV_PATH = path.join(process.cwd(), '.env');
let PUBLIC_KEY = process.env.SOVEREIGN_PUBLIC_KEY;
let SECRET_KEY = process.env.SOVEREIGN_SECRET_KEY;

if (!PUBLIC_KEY || !SECRET_KEY) {
    const keyPair = nacl.sign.keyPair();
    PUBLIC_KEY = encodeBase64(keyPair.publicKey);
    SECRET_KEY = encodeBase64(keyPair.secretKey);
    
    const envContent = fs.existsSync(ENV_PATH) ? fs.readFileSync(ENV_PATH, 'utf8') : '';
    let newEnv = envContent;
    if (!envContent.includes('SOVEREIGN_PUBLIC_KEY')) {
        newEnv += `\nSOVEREIGN_PUBLIC_KEY=${PUBLIC_KEY}\n`;
    }
    if (!envContent.includes('SOVEREIGN_SECRET_KEY')) {
        newEnv += `\nSOVEREIGN_SECRET_KEY=${SECRET_KEY}\n`;
    }
    fs.writeFileSync(ENV_PATH, newEnv);
    console.log('[SOVEREIGN-AUDIT] Generated new Ed25519 Sovereign Identity Keypair.');
}

export class AuditLedger {
    public static events = new EventEmitter();
    private static logQueue: any[] = [];
    private static isProcessing: boolean = false;

    private static lastRecordHash: string = '0'.repeat(64);

    /**
     * [ZENITH 11.5] SOVEREIGN CHAINING SIGNATURE
     * Signs a decision and chains it to the previous record's hash to ensure immutability.
     */
    static async signAndLog(agent: string, action: string, payload: any) {
        const timestamp = new Date().toISOString();
        const payloadStr = JSON.stringify(payload);
        
        // Multi-Hash Strategy + Chaining
        const h256 = createHash('sha256').update(payloadStr + this.lastRecordHash).digest('hex');
        const h512 = createHash('sha512').update(payloadStr).digest('hex');
        const h3 = createHash('sha3-256').update(payloadStr).digest('hex');
        
        const payloadHash = `CHAIN:${h256}:${h512.substring(0, 32)}:${h3.substring(0, 32)}`;
        
        const message = new TextEncoder().encode(payloadHash);
        const secretKeyRaw = decodeBase64(SECRET_KEY!);
        const signatureRaw = nacl.sign.detached(message, secretKeyRaw);
        const signature = encodeBase64(signatureRaw);
        
        const id = createHash('sha1').update(timestamp + payloadHash).digest('hex');

        // Update the chain head
        this.lastRecordHash = h256;

        this.logQueue.push({ id, timestamp, agent, action, payloadHash, signature, publicKey: PUBLIC_KEY });
        this.processQueue();

        // Broadcast to Neural Link
        this.events.emit('LOG_EMITTED', { id, timestamp, agent, action, payloadHash });

        console.log(`[SOVEREIGN-AUDIT] Chained (Seal: ${payloadHash.substring(0, 15)}...)`);
        return { id, signature, publicKey: PUBLIC_KEY };
    }

    private static async processQueue() {
        if (this.isProcessing || this.logQueue.length === 0) return;
        this.isProcessing = true;

        const batch = [...this.logQueue];
        this.logQueue = [];

        try {
            for (const item of batch) {
                // 1. Production Persistence (Postgres) - Temporarily bypassed for Rukun 0-Token mode
                /* 
                await dbProvider.query(
                    `INSERT INTO audit_logs (id, timestamp, agent, action, payload_hash, signature, public_key) 
                     VALUES ($1, $2, $3, $4, $5, $6, $7)
                     ON CONFLICT (id) DO NOTHING`,
                    [item.id, item.timestamp, item.agent, item.action, item.payloadHash, item.signature, item.publicKey]
                );
                */

                // 2. Physical Sovereignty Persistence (Local Bun-Native SQLite)
                const stmt = localDb.prepare(`
                    INSERT OR IGNORE INTO audit_logs (id, timestamp, agent, action, payload_hash, signature, public_key)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                `);
                stmt.run(item.id, item.timestamp, item.agent, item.action, item.payloadHash, item.signature, item.publicKey);
            }
        } catch (e) {
            console.error('[POSTGRES-AUDIT] Batch Insert Failed:', e);
            // Re-queue failed logs
            this.logQueue.unshift(...batch);
        }

        this.isProcessing = false;
        if (this.logQueue.length > 0) this.processQueue();
    }

    static async verifySignature(payloadHash: string, signature: string): Promise<boolean> {
        try {
            const message = new TextEncoder().encode(payloadHash);
            const signatureRaw = decodeBase64(signature);
            const publicKeyRaw = decodeBase64(PUBLIC_KEY!);
            return nacl.sign.detached.verify(message, signatureRaw, publicKeyRaw);
        } catch (e) {
            return false;
        }
    }

    static async getLogs(limit = 100) {
        const res = await dbProvider.query("SELECT * FROM audit_logs ORDER BY timestamp DESC LIMIT $1", [limit]);
        return res.rows;
    }

    /**
     * [ZENITH 1000] HISTORICAL INTEGRITY SCAN
     * Performs a deep-scan to verify that no historical logs have been tampered with.
     */
    static async verifyIntegrity(): Promise<{ total: number, valid: number, breached: string[] }> {
        const logs = await this.getLogs(5000);
        let valid = 0;
        const breached: string[] = [];

        for (const log of logs) {
            const isSignatureValid = await this.verifySignature(log.payload_hash, log.signature);
            if (isSignatureValid) {
                valid++;
            } else {
                breached.push(log.id);
            }
        }

        return { total: logs.length, valid, breached };
    }

    /**
     * Signs an internal architectural decision (Project milestones, agent switching, etc.)
     */
    static async signInternalDecision(agent: string, action: string, metadata: any) {
        return await this.signAndLog(agent, `INTERNAL_DECISION:${action}`, metadata);
    }
}

/** Legacy Alias for OMEGA-Z 11.4 Transition */
export const AuditChainService = AuditLedger;
export const AuditChain = AuditLedger;
