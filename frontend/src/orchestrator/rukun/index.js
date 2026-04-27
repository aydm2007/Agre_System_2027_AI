import { ProjectAnalyzer } from './project_analyzer';
import { AuditLedger } from '../../utils/auditLedger';

export const RukunMode = {
  version: '14.0.0',

  async activate() {
    const diagnostic = await ProjectAnalyzer.runDiagnostic();

    await AuditLedger.signAndLog('RUKUN_CORE', 'MODE_ACTIVATION', {
      version: this.version,
      diagnostic,
    });

    return {
      status: diagnostic.status,
      report: diagnostic,
    };
  },
};

export default RukunMode;
