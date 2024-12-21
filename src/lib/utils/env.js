export async function getEnvVariables() {
  try {
    // Get all environment variables from import.meta.env
    const envVariables = Object.entries(import.meta.env)
      .filter(([key]) => key.startsWith('VITE_')) // Only show VITE_ prefixed vars for security
      .map(([key, value]) => ({
        key,
        value: value || ''
      }));

    return envVariables;
  } catch (error) {
    console.error('Error loading environment variables:', error);
    return [];
  }
}
