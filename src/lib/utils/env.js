import dotenv from 'dotenv';

export async function getEnvVariables() {
  try {
    // Load environment variables from .env file
    dotenv.config();
    
    // Filter and map environment variables
    const envVariables = Object.entries(process.env)
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
