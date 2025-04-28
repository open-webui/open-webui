const wsLib = require("ws");
const fs = require("fs");
const path = require("path");
const dotenv = require("dotenv");
const dotenvExpand = require("dotenv-expand");

async function loadEnvFile() {
  const domain = process.env.WORKSPACE_DEV_DOMAIN || "";
  let envFile;
  let apiDomain;

  if (domain.includes("codesphere.com")) {
    envFile = ".env.codesphere";
    apiDomain = "codesphere.com";
  } else {
    envFile = ".env.local";
  }

  const envDefaultPath = path.resolve(__dirname, "..", ".env");
  const envPath = path.resolve(__dirname, "..", envFile);
  console.log(envPath);
  if (fs.existsSync(envPath)) {
    dotenvExpand.expand(dotenv.config({ path: envDefaultPath }));
    dotenvExpand.expand(dotenv.config({ path: envPath }));

    const envConfigDefault = dotenv.parse(fs.readFileSync(envDefaultPath));
    const envConfigSpecific = dotenv.parse(fs.readFileSync(envPath));

    // Merge default .env and specific .env.<landscape>
    const envConfig = Object.assign({}, envConfigDefault, envConfigSpecific);

    const config = {};
    for (let [key, value] of Object.entries(envConfig)) {
      if (key.includes("DIR") || key.includes("PATH")) {
        config[key] = path.resolve(value);
      } else {
        config[key] = value;
      }
    }
    console.log(`Loaded environment from ${envFile}`);
    return { config, apiDomain };
  } else {
    console.error(`.env file ${envFile} not found`);
  }
}

async function main() {
  try {
    let { config, apiDomain } = await loadEnvFile();

    // All env vars to be set in all type of workspaces
    config = {
      ...config,
      // VITE_WORKSPACE_ID: process.env.WORKSPACE_ID,
      // VITE_WORKSPACE_DEV_URL: `https://${process.env.WORKSPACE_DEV_DOMAIN}`,
    };

    let envRequest = [];
    for (let [key, value] of Object.entries(config)) {
      envRequest.push({
        name: key,
        value: value,
      });
    }

    // Send request to put env vars
    let flowResult = await fetch(
      `https://${apiDomain}/api/workspaces/${process.env.WORKSPACE_ID}/env-vars`,
      {
        method: "PUT",
        headers: {
          "Content-Type": "application/json",
          Authorization: "Bearer " + process.env.INTERNAL_API_KEY,
        },
        body: JSON.stringify(envRequest),
      }
    );
    if (flowResult.status != 200) {
      throw new Error(`Failed to update Env Vars. flowResult status: (${flowResult.status})`);
    }
    
    // Exit the process
    process.exit(0);
  } catch (error) {
    console.error("Error:", error);
    process.exit(1);
  }
}

main();