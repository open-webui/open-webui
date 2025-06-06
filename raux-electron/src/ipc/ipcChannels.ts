export class IPCChannels {
  static readonly INSTALLATION_STATUS = 'installation:status';
  static readonly INSTALLATION_PROGRESS = 'installation:progress';
  static readonly INSTALLATION_ERROR = 'installation:error';
  static readonly INSTALLATION_COMPLETE = 'installation:complete';
  static readonly INSTALLATION_RETRY = 'installation:retry';
  static readonly LEMONADE_STATUS = 'lemonade:status';
  static readonly LEMONADE_HEALTH_CHECK = 'lemonade:health-check';
} 