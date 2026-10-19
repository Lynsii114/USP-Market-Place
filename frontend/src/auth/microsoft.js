/* FUTURE MICROSOFT ENTRA INTEGRATION.
 * Uncomment this file when USP provides the Entra tenant and client IDs.
import { PublicClientApplication } from "@azure/msal-browser";

const clientId = import.meta.env.VITE_MICROSOFT_CLIENT_ID || "";
const tenantId = import.meta.env.VITE_MICROSOFT_TENANT_ID || "common";

export const microsoftLoginAvailable = Boolean(clientId);

const msalInstance = microsoftLoginAvailable
  ? new PublicClientApplication({
      auth: {
        clientId,
        authority: `https://login.microsoftonline.com/${tenantId}`,
        redirectUri: window.location.origin,
      },
      cache: {
        cacheLocation: "sessionStorage",
      },
    })
  : null;

export const microsoftLogin = async () => {
  if (!msalInstance) {
    throw new Error("Microsoft sign-in is not configured");
  }

  await msalInstance.initialize();
  const response = await msalInstance.loginPopup({
    scopes: ["openid", "profile", "email"],
  });
  return response.idToken;
};
*/