import { PublicClientApplication } from '@azure/msal-browser';

const msalParams = {
  auth: {
    authority: 'https://login.microsoftonline.com/consumers',
    clientId: '2ab80a1e-7300-4cb1-beac-c38c730e8b7f'
  }
};

// MSAL 초기화
const app = new PublicClientApplication(msalParams);

export async function initializeMsal() {
    try {
      await app.initialize();
      console.log('MSAL initialized successfully');
    } catch (error) {
      console.error('MSAL initialization error:', error);
    }
  }

  export async function getToken(): Promise<string> {
    const authParams = { scopes: ['OneDrive.ReadWrite'] };
    let accessToken = '';
  
    try {
      // Ensure initialization happens early
      await initializeMsal();  
      const resp = await app.acquireTokenSilent(authParams);
      accessToken = resp.accessToken;
    } catch (err) {
      const resp = await app.loginPopup(authParams);
      app.setActiveAccount(resp.account);
  
      if (resp.idToken) {
        const resp2 = await app.acquireTokenSilent(authParams);
        accessToken = resp2.accessToken;
      }
    }
  
    return accessToken;
  }
