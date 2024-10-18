# Rishika WebUI Backend Setup

This document outlines the steps to set up and run the backend of Rishika WebUI.

---

## Prerequisites

Ensure you have the following installed:
- Node.js and npm
- Python and virtual environment tools

---

## Step-by-Step Backend Setup Instructions

1. **Navigate to the `open-webui` directory**:

    ```bash
    cd open-webui
    ```

2. **Change directory to the backend**:

    ```bash
    cd backend
    ```

3. **Build the backend using npm**:

    To build the necessary backend files, run:

    ```bash
    npm run build
    ```

4. **Activate the Python virtual environment**:

    Ensure you have set up your Python virtual environment. To activate it:

    ```bash
    source rishika/bin/activate
    ```

5. **Run the backend in the background**:

    Use `nohup` to run the backend process in the background. This will log the output into `openwebui.log`:

    ```bash
    nohup ./start.sh > openwebui.log 2>&1 &
    ```

6. **Monitor the logs**:

    To monitor the backend logs in real-time, use the `tail` command:

    ```bash
    tail -f openwebui.log
    ```

---

## Additional Notes

- Ensure the `start.sh` script has the appropriate executable permissions. If not, you can give the file executable rights using:

    ```bash
    chmod +x start.sh
    ```

- In case you encounter issues during the process, refer to the logs (`openwebui.log`) for error details or troubleshoot further.

---

## Conclusion

You should now have the Rishika WebUI backend set up and running. For further details or troubleshooting, consult the project documentation or join the community for support.
