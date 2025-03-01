import { WEBUI_API_BASE_URL } from '$lib/constants';
export interface FileMetadata {
  id: string;
  name: string;
  path: string;
  meta: {
    name: string;
    content_type: string;
    size: number;
  };
}

export const processGoogleDriveLink = async (token: string, driveId: string): Promise<FileMetadata[]> => {
  if (!WEBUI_API_BASE_URL) {
    throw new Error("WEBUI_API_BASE_URL is not defined.");
  }

  const response = await fetch(`${WEBUI_API_BASE_URL}/google-drive/`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "Authorization": `Bearer ${token}`,
    },
    body: JSON.stringify({ driveId }), // Send the driveId in the request body
  });

  // Handle errors from backend
  if (!response.ok) {
    const errorDetails = await response.text();
    throw new Error(`Failed to process Google Drive link (Status: ${response.status}, Details: ${errorDetails})`);
  }

  // Parse the response JSON
  const result: { files_metadata: FileMetadata[] } = await response.json();

  // Validate the response structure
  if (!Array.isArray(result.files_metadata)) {
    throw new Error("Invalid response format: Expected 'files_metadata' to be an array.");
  }

  // Return file metadata
  return result.files_metadata;
};