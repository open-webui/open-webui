from fastapi import APIRouter, HTTPException, Request, Depends, status
from fastapi.responses import JSONResponse
import traceback

from open_webui.utils.driveService import process_google_drive_link
from open_webui.utils.auth import get_verified_user

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
        drive_link = data.get("link")
        user_id = user.id
        
        # Validate input
        if not drive_link or not user_id:
            raise HTTPException(status_code=400, detail="Missing required fields.")
        
        # Call utility function to handle Google Drive logic
        result = await process_google_drive_link(drive_link=drive_link, user=user, request=request)
        # print("\n")
        # print(result)
        # print("this is res")
        # Return success response with metadata
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "message": f"Successfully processed files from Drive ID: {drive_link}",
                "files_metadata": result['files_metadata'],
            },
        )
    
    except HTTPException as http_error:
        raise http_error
    
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error processing Drive link: {str(e)}")
