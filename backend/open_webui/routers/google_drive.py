from fastapi import APIRouter, HTTPException, Request, Depends
from fastapi.responses import JSONResponse
from fastapi import status
from open_webui.utils.driveService import process_google_drive_link
from open_webui.utils.auth import get_verified_user
import traceback

router = APIRouter()

@router.post("/")
async def process_drive_link(request: Request, user=Depends(get_verified_user)):
    """
    Process a Google Drive link, fetch its files, upload them, and return their metadata.
    Args:
        request (Request): HTTP request containing Google Drive ID.
        user (Depends): The authenticated user.
    Returns:
        JSONResponse: Contains metadata for the successfully uploaded files.
    """
    try:
        # Parse incoming request body
        data = await request.json()
        drive_id = data.get("driveId")
        user_id = user.id
        print(user_id)
        
        # Validate input
        if not drive_id or not user_id:
            raise HTTPException(status_code=400, detail="Missing required fields.")

        # Call utility function to handle Google Drive logic
        result = await process_google_drive_link(drive_id=drive_id, user_id=user_id, request=request)

        # Return success response with metadata
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "message": f"Successfully processed files from Drive ID: {drive_id}",
                "files_metadata": result,
            },
        )
    except HTTPException as http_error:
        raise http_error
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error processing Drive link: {str(e)}")