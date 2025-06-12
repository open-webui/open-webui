from datetime import datetime, timedelta

from fastapi import HTTPException, Depends
from fastapi.params import Query

from beyond_the_loop.models.users import get_users_by_company, get_active_users_by_company
from open_webui.internal.db import get_db
from beyond_the_loop.models.completions import Completion
from beyond_the_loop.models.users import User
from beyond_the_loop.models.models import Model

from sqlalchemy import func

from fastapi import APIRouter

import logging

from open_webui.env import SRC_LOG_LEVELS
from open_webui.utils.auth import get_verified_user

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["MODELS"])

router = APIRouter()

@router.get("/top-models")
async def get_top_models(
    start_date: str = Query(None, description="Start date in YYYY-MM-DD format"),
    end_date: str = Query(None, description="End date in YYYY-MM-DD format"),
    user=Depends(get_verified_user)
):
    """
    Returns the top 5 models based on usage for the user's company within the specified date range.
    """
    try:
        if start_date:
            start_date_dt = datetime.strptime(start_date, "%Y-%m-%d")
            start_timestamp = int(start_date_dt.timestamp())
        else:
            raise HTTPException(status_code=400, detail="Start date is required.")

        if end_date:
            end_date_dt = datetime.strptime(end_date, "%Y-%m-%d")
            end_date_dt = datetime(end_date_dt.year, end_date_dt.month, end_date_dt.day, 23, 59, 59)
            end_timestamp = int(end_date_dt.timestamp())
        else:
            end_date_dt = datetime.now()
            end_date_dt = datetime(end_date_dt.year, end_date_dt.month, end_date_dt.day, 23, 59, 59)
            end_timestamp = int(end_date_dt.timestamp())

        if start_timestamp > end_timestamp:
            raise HTTPException(status_code=400, detail="Start date must be before end date.")

        with get_db() as db:
            top_models = db.query(
                Completion.model,
                func.sum(Completion.credits_used).label("credits_used")
            ).filter(
                Completion.created_at >= start_timestamp,
                Completion.created_at <= end_timestamp,
                Completion.user_id == user.id
            ).group_by(
                Completion.model
            ).order_by(
                func.sum(Completion.credits_used).desc()
            ).limit(3).all()

        if not top_models:
            return {"message": "No data found for the given parameters."}

        return [{"model": model, "credits_used": credit_sum} for model, credit_sum in top_models]
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching top models: {e}")


@router.get("/top-users")
async def get_top_users(
    start_date: str = Query(None, description="Start date in YYYY-MM-DD format"),
    end_date: str = Query(None, description="End date in YYYY-MM-DD format"),
    user=Depends(get_verified_user)
):
    """
    Returns the top users based on different metrics (credits used, messages, assistants created)
    for the user's company and within a specified date range.
    """
    try:
        if start_date:
            start_date_dt = datetime.strptime(start_date, "%Y-%m-%d")
            start_timestamp = int(start_date_dt.timestamp())
        else:
            raise HTTPException(status_code=400, detail="Start date is required.")

        if end_date:
            end_date_dt = datetime.strptime(end_date, "%Y-%m-%d")
            end_date_dt = datetime(end_date_dt.year, end_date_dt.month, end_date_dt.day, 23, 59, 59)
            end_timestamp = int(end_date_dt.timestamp())
        else:
            end_date_dt = datetime.now()
            end_date_dt = datetime(end_date_dt.year, end_date_dt.month, end_date_dt.day, 23, 59, 59)
            end_timestamp = int(end_date_dt.timestamp())

        if start_timestamp > end_timestamp:
            raise HTTPException(status_code=400, detail="Start date must be before end date.")

        with get_db() as db:
            # Query top users by credits used
            top_users_by_credits = db.query(
                Completion.user_id,
                func.sum(Completion.credits_used).label("total_credits"),
                User.first_name,
                User.last_name,
                User.email,
                User.profile_image_url
            ).join(
                User, User.id == Completion.user_id
            ).filter(
                Completion.created_at >= start_timestamp,
                Completion.created_at <= end_timestamp,
                User.company_id == user.company_id
            ).group_by(
                Completion.user_id, User.first_name, User.last_name, User.email, User.profile_image_url
            ).order_by(
                func.sum(Completion.credits_used).desc()
            ).limit(5).all()

            # Query top users by message count
            top_users_by_messages = db.query(
                Completion.user_id,
                func.count(Completion.id).label("message_count"),
                User.first_name,
                User.last_name,
                User.email,
                User.profile_image_url
            ).join(
                User, User.id == Completion.user_id
            ).filter(
                Completion.created_at >= start_timestamp,
                Completion.created_at <= end_timestamp,
                User.company_id == user.company_id
            ).group_by(
                Completion.user_id, User.first_name, User.last_name, User.email, User.profile_image_url
            ).order_by(
                func.count(Completion.id).desc()
            ).limit(5).all()

            # Query top users by assistants created
            top_users_by_assistants = db.query(
                Model.user_id,
                func.count(Model.id).label("assistant_count"),
                User.first_name,
                User.last_name,
                User.email,
                User.profile_image_url
            ).join(
                User, User.id == Model.user_id
            ).filter(
                Model.created_at >= start_timestamp,
                Model.created_at <= end_timestamp,
                Model.company_id == user.company_id
            ).group_by(
                Model.user_id, User.first_name, User.last_name, User.email, User.profile_image_url
            ).order_by(
                func.count(Model.id).desc()
            ).limit(5).all()

        # Format results for credits
        top_by_credits = [
            {
                "user_id": user_id,
                "first_name": first_name,
                "last_name": last_name,
                "email": email,
                "profile_image_url": profile_image_url,
                "total_credits_used": total_credits
            }
            for user_id, total_credits, first_name, last_name, email, profile_image_url in top_users_by_credits
        ]

        # Format results for messages
        top_by_messages = [
            {
                "user_id": user_id,
                "first_name": first_name,
                "last_name": last_name,
                "email": email,
                "profile_image_url": profile_image_url,
                "message_count": message_count
            }
            for user_id, message_count, first_name, last_name, email, profile_image_url in top_users_by_messages
        ]

        # Format results for assistants
        top_by_assistants = [
            {
                "user_id": user_id,
                "first_name": first_name,
                "last_name": last_name,
                "email": email,
                "profile_image_url": profile_image_url,
                "assistant_count": assistant_count
            }
            for user_id, assistant_count, first_name, last_name, email, profile_image_url in top_users_by_assistants
        ]

        return {
            "top_by_credits": top_by_credits,
            "top_by_messages": top_by_messages,
            "top_by_assistants": top_by_assistants
        }
    except ValueError as ve:
        # Add more detailed error information
        log.error(f"ValueError in get_top_users: {ve}")
        raise HTTPException(status_code=400, detail=f"Invalid date format. Use YYYY-MM-DD. Error: {ve}")
    except Exception as e:
        # Log the specific error
        log.error(f"Error in get_top_users: {e}")
        raise HTTPException(status_code=500, detail=f"Error fetching top users: {e}")


@router.get("/stats/total-billing")
async def get_total_billing(
    start_date: str = Query(None, description="Start date in YYYY-MM-DD format (optional)"),
    end_date: str = Query(None, description="End date in YYYY-MM-DD format (optional)"),
    user=Depends(get_verified_user)
):
    """
    Returns total billing data for the last 12 months or within a specified time frame,
    filtered by the user's company.
    """
    try:
        current_date = datetime.now()
        one_year_ago = current_date.replace(day=1) - timedelta(days=365)

        # Parse start_date
        if start_date:
            start_date_dt = datetime.strptime(start_date, "%Y-%m-%d")
        else:
            start_date_dt = one_year_ago  # Default to one year ago

        # Parse end_date
        if end_date:
            end_date_dt = datetime.strptime(end_date, "%Y-%m-%d")
            end_date_dt = datetime(end_date_dt.year, end_date_dt.month, end_date_dt.day, 23, 59, 59)
        else:
            end_date_dt = current_date  # Default to current date
            end_date_dt = datetime(end_date_dt.year, end_date_dt.month, end_date_dt.day, 23, 59, 59)

        if start_date_dt > end_date_dt:
            raise HTTPException(status_code=400, detail="Start date must be before end date.")

        with get_db() as db:
            query = db.query(
                func.strftime('%Y-%m', func.datetime(Completion.created_at, 'unixepoch')).label("month"),
                func.sum(Completion.credits_used).label("total_billing")
            ).filter(
                func.datetime(Completion.created_at, 'unixepoch') >= start_date_dt.strftime('%Y-%m-%d 00:00:00'),
                func.datetime(Completion.created_at, 'unixepoch') <= end_date_dt.strftime('%Y-%m-%d %H:%M:%S')
            )

            query = query.filter(Completion.user_id == user.id)

            # Execute the query and fetch results
            results = query.group_by("month").order_by("month").all()

            # Convert results to a dictionary
            monthly_billing = {row[0]: float(row[1]) for row in results}

        # Generate all months within the specified range
        months = []
        current_month = start_date_dt.replace(day=1)
        end_month = end_date_dt.replace(day=1)

        while current_month <= end_month:
            months.append(current_month.strftime('%Y-%m'))
            # Move to the first day of next month
            if current_month.month == 12:
                current_month = current_month.replace(year=current_month.year + 1, month=1)
            else:
                current_month = current_month.replace(month=current_month.month + 1)

        billing_data = {month: monthly_billing.get(month, 0) for month in months}

        # Calculate percentage changes month-over-month
        percentage_changes = {}
        previous_value = None
        for month, value in billing_data.items():
            if previous_value is not None:
                change = ((value - previous_value) / previous_value) * 100 if previous_value != 0 else None
                percentage_changes[month] = round(change, 2) if change is not None else "N/A"
            else:
                percentage_changes[month] = "N/A"
            previous_value = value

        return {
            "monthly_billing": billing_data,
            "percentage_changes": percentage_changes
        }
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching billing stats: {e}")


@router.get("/stats/total-messages")
async def get_total_messages(
    start_date: str = Query(None, description="Start date in YYYY-MM-DD format (optional)"),
    end_date: str = Query(None, description="End date in YYYY-MM-DD format (optional)"),
    user=Depends(get_verified_user)
):
    """
    Returns total number of completions for the last 12 months or within a specified time frame,
    filtered by the user's company.
    """
    try:
        current_date = datetime.now()
        one_year_ago = current_date.replace(day=1) - timedelta(days=365)

        # Parse start_date
        if start_date:
            start_date_dt = datetime.strptime(start_date, "%Y-%m-%d")
        else:
            start_date_dt = one_year_ago  # Default to one year ago

        # Parse end_date
        if end_date:
            end_date_dt = datetime.strptime(end_date, "%Y-%m-%d")
            end_date_dt = datetime(end_date_dt.year, end_date_dt.month, end_date_dt.day, 23, 59, 59)
        else:
            end_date_dt = current_date  # Default to current date
            end_date_dt = datetime(end_date_dt.year, end_date_dt.month, end_date_dt.day, 23, 59, 59)

        if start_date_dt > end_date_dt:
            raise HTTPException(status_code=400, detail="Start date must be before end date.")

        with get_db() as db:
            query = db.query(
                func.strftime('%Y-%m', func.datetime(Completion.created_at, 'unixepoch')).label("month"),
                func.count(Completion.id).label("total_messages")
            ).filter(
                func.datetime(Completion.created_at, 'unixepoch') >= start_date_dt.strftime('%Y-%m-%d 00:00:00'),
                func.datetime(Completion.created_at, 'unixepoch') <= end_date_dt.strftime('%Y-%m-%d %H:%M:%S')
            )

            query = query.filter(Completion.user_id == user.id)

            # Execute the query and fetch results
            results = query.group_by("month").order_by("month").all()

            # Convert results to a dictionary
            monthly_messages = {row[0]: int(row[1]) for row in results}

        # Generate all months within the specified range
        months = []
        current_month = start_date_dt.replace(day=1)
        end_month = end_date_dt.replace(day=1)

        while current_month <= end_month:
            months.append(current_month.strftime('%Y-%m'))
            # Move to the first day of next month
            if current_month.month == 12:
                current_month = current_month.replace(year=current_month.year + 1, month=1)
            else:
                current_month = current_month.replace(month=current_month.month + 1)

        message_data = {month: monthly_messages.get(month, 0) for month in months}

        # Calculate percentage changes month-over-month
        percentage_changes = {}
        previous_value = None
        for month, value in message_data.items():
            if previous_value is not None:
                change = ((value - previous_value) / previous_value) * 100 if previous_value != 0 else None
                percentage_changes[month] = round(change, 2) if change is not None else "N/A"
            else:
                percentage_changes[month] = "N/A"
            previous_value = value

        return {
            "monthly_messages": message_data,
            "percentage_changes": percentage_changes
        }
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching message stats: {e}")


@router.get("/stats/total-chats")
async def get_total_chats(
    start_date: str = Query(None, description="Start date in YYYY-MM-DD format (optional)"),
    end_date: str = Query(None, description="End date in YYYY-MM-DD format (optional)"),
    user=Depends(get_verified_user)
):
    """
    Returns total number of unique chats for the last 12 months or within a specified time frame,
    filtered by the user's company.
    """
    try:
        current_date = datetime.now()
        one_year_ago = current_date.replace(day=1) - timedelta(days=365)

        # Parse start_date
        if start_date:
            start_date_dt = datetime.strptime(start_date, "%Y-%m-%d")
        else:
            start_date_dt = one_year_ago  # Default to one year ago

        # Parse end_date
        if end_date:
            end_date_dt = datetime.strptime(end_date, "%Y-%m-%d")
            end_date_dt = datetime(end_date_dt.year, end_date_dt.month, end_date_dt.day, 23, 59, 59)
        else:
            end_date_dt = current_date  # Default to current date
            end_date_dt = datetime(end_date_dt.year, end_date_dt.month, end_date_dt.day, 23, 59, 59)

        if start_date_dt > end_date_dt:
            raise HTTPException(status_code=400, detail="Start date must be before end date.")

        with get_db() as db:
            query = db.query(
                func.strftime('%Y-%m', func.datetime(Completion.created_at, 'unixepoch')).label("month"),
                func.count(func.distinct(Completion.chat_id)).label("total_chats")
            ).filter(
                func.datetime(Completion.created_at, 'unixepoch') >= start_date_dt.strftime('%Y-%m-%d 00:00:00'),
                func.datetime(Completion.created_at, 'unixepoch') <= end_date_dt.strftime('%Y-%m-%d %H:%M:%S')
            )

            query = query.filter(Completion.user_id == user.id)

            # Execute the query and fetch results
            results = query.group_by("month").order_by("month").all()

            # Convert results to a dictionary
            monthly_chats = {row[0]: int(row[1]) for row in results}

        # Generate all months within the specified range
        months = []
        current_month = start_date_dt.replace(day=1)
        end_month = end_date_dt.replace(day=1)

        while current_month <= end_month:
            months.append(current_month.strftime('%Y-%m'))
            # Move to the first day of next month
            if current_month.month == 12:
                current_month = current_month.replace(year=current_month.year + 1, month=1)
            else:
                current_month = current_month.replace(month=current_month.month + 1)

        chat_data = {month: monthly_chats.get(month, 0) for month in months}

        # Calculate percentage changes month-over-month
        percentage_changes = {}
        previous_value = None
        for month, value in chat_data.items():
            if previous_value is not None:
                change = ((value - previous_value) / previous_value) * 100 if previous_value != 0 else None
                percentage_changes[month] = round(change, 2) if change is not None else "N/A"
            else:
                percentage_changes[month] = "N/A"
            previous_value = value

        return {
            "monthly_chats": chat_data,
            "percentage_changes": percentage_changes
        }
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching chat stats: {e}")


@router.get("/stats/saved-time-in-seconds")
async def get_saved_time_in_seconds(
    start_date: str = Query(None, description="Start date in YYYY-MM-DD format (optional)"),
    end_date: str = Query(None, description="End date in YYYY-MM-DD format (optional)"),
    user=Depends(get_verified_user)
):
    """
    Returns total saved time in seconds for the last 12 months or within a specified time frame,
    filtered by the user's completions.
    """
    try:
        current_date = datetime.now()
        one_year_ago = current_date.replace(day=1) - timedelta(days=365)

        # Parse start_date
        if start_date:
            start_date_dt = datetime.strptime(start_date, "%Y-%m-%d")
        else:
            start_date_dt = one_year_ago  # Default to one year ago

        # Parse end_date
        if end_date:
            end_date_dt = datetime.strptime(end_date, "%Y-%m-%d")
            end_date_dt = datetime(end_date_dt.year, end_date_dt.month, end_date_dt.day, 23, 59, 59)
        else:
            end_date_dt = current_date  # Default to current date
            end_date_dt = datetime(end_date_dt.year, end_date_dt.month, end_date_dt.day, 23, 59, 59)

        if start_date_dt > end_date_dt:
            raise HTTPException(status_code=400, detail="Start date must be before end date.")

        with get_db() as db:
            query = db.query(
                func.strftime('%Y-%m', func.datetime(Completion.created_at, 'unixepoch')).label("month"),
                func.sum(Completion.time_saved_in_seconds).label("total_saved_time")
            ).filter(
                func.datetime(Completion.created_at, 'unixepoch') >= start_date_dt.strftime('%Y-%m-%d 00:00:00'),
                func.datetime(Completion.created_at, 'unixepoch') <= end_date_dt.strftime('%Y-%m-%d %H:%M:%S')
            )

            query = query.filter(Completion.user_id == user.id)

            # Execute the query and fetch results
            results = query.group_by("month").order_by("month").all()

            # Convert results to a dictionary
            monthly_saved_time = {row[0]: int(row[1]) if row[1] is not None else 0 for row in results}

        # Generate all months within the specified range
        months = []
        current_month = start_date_dt.replace(day=1)
        end_month = end_date_dt.replace(day=1)

        while current_month <= end_month:
            months.append(current_month.strftime('%Y-%m'))
            # Move to the first day of next month
            if current_month.month == 12:
                current_month = current_month.replace(year=current_month.year + 1, month=1)
            else:
                current_month = current_month.replace(month=current_month.month + 1)

        saved_time_data = {month: monthly_saved_time.get(month, 0) for month in months}

        # Calculate percentage changes month-over-month
        percentage_changes = {}
        previous_value = None
        for month, value in saved_time_data.items():
            if previous_value is not None:
                change = ((value - previous_value) / previous_value) * 100 if previous_value != 0 else None
                percentage_changes[month] = round(change, 2) if change is not None else "N/A"
            else:
                percentage_changes[month] = "N/A"
            previous_value = value

        return {
            "monthly_saved_time_in_seconds": saved_time_data,
            "percentage_changes": percentage_changes
        }
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching saved time stats: {e}")


@router.get("/stats/total-users")
async def get_total_users(user=Depends(get_verified_user)):
    """
    Returns the total number of users that have an account for the user's company.
    """
    try:
        return {"total_users": len(get_users_by_company(user.company_id))}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching total users: {e}")


@router.get("/stats/adoption-rate")
async def get_adoption_rate(user=Depends(get_verified_user)):
    """
    Returns the adoption rate: percentage of users for the user's company 
    that logged in in the last 30 days.
    """
    try:
        # Calculate timestamp for 30 days ago
        thirty_days_ago = int((datetime.now() - timedelta(days=30)).timestamp())

        with get_db() as db:
            # Get total number of users in the company
            total_users = len(get_users_by_company(user.company_id))

            # Get number of active users in the last 30 days
            active_users = len(get_active_users_by_company(user.company_id, thirty_days_ago))

            # Calculate adoption rate as a percentage
            adoption_rate = (active_users / total_users * 100) if total_users > 0 else 0

        return {
            "total_users": total_users,
            "active_users": active_users,
            "adoption_rate": round(adoption_rate, 2)  # Round to 2 decimal places
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error calculating adoption rate: {e}")


@router.get("/stats/power-users")
async def get_power_users(user=Depends(get_verified_user)):
    """
    Returns users for the user's company that wrote more than 400 messages 
    in the last 30 days.
    """
    try:
        # Calculate timestamp for 30 days ago
        thirty_days_ago = int((datetime.now() - timedelta(days=30)).timestamp())

        with get_db() as db:
            # Find users with more than 400 messages in the last 30 days
            power_users_query = db.query(
                User.id,
                User.first_name,
                User.last_name,
                User.email,
                User.profile_image_url,
                func.count(Completion.id).label("message_count")
            ).join(
                Completion, User.id == Completion.user_id
            ).filter(
                User.company_id == user.company_id,
                Completion.created_at >= thirty_days_ago
            ).group_by(
                User.id, User.first_name, User.last_name, User.email, User.profile_image_url
            ).having(
                func.count(Completion.id) > 400
            ).order_by(
                func.count(Completion.id).desc()
            ).all()

            # Format the results
            power_users = [
                {
                    "user_id": user_id,
                    "first_name": first_name,
                    "last_name": last_name,
                    "email": email,
                    "profile_image_url": profile_image_url,
                    "message_count": message_count
                }
                for user_id, first_name, last_name, email, profile_image_url, message_count in power_users_query
            ]

            # Get total number of users in the company for percentage calculation
            total_users = len(get_users_by_company(user.company_id))

            # Calculate percentage of power users
            power_users_percentage = (len(power_users) / total_users * 100) if total_users > 0 else 0

        return {
            "power_users": power_users,
            "power_users_count": len(power_users),
            "total_users": total_users,
            "power_users_percentage": round(power_users_percentage, 2)  # Round to 2 decimal places
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching power users: {e}")


@router.get("/stats/total-assistants")
async def get_total_assistants(user=Depends(get_verified_user)):
    """
    Returns the total number of assistants (models) that are available for the user's company.
    """
    try:
        with get_db() as db:
            # Query models that belong to the user's company
            total_assistants = db.query(Model).filter(
                Model.company_id == user.company_id,
                Model.base_model_id != None
            ).count()
            
            return {"total_assistants": total_assistants}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching total assistants: {e}")
