from fastapi import APIRouter, Depends, HTTPException
from typing import List
from app.models.booking import Booking
from app.models.user import User
from app.schemas.booking import BookingIn, BookingOut
from app.core.security import get_current_user

router = APIRouter()

@router.get("/my-bookings", response_model=List[BookingOut])
async def my_bookings(current_user: User = Depends(get_current_user)):
    """List bookings for the current authenticated user."""
    print(f"Current user: {current_user}")  # Debug log
    try:
        bookings = await Booking.filter(user_id=current_user.id)
        print(f"Found bookings: {bookings}")  # Debug log
        return bookings
    except Exception as e:
        print(f"Error in my_bookings: {str(e)}")  # Debug log
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching bookings: {str(e)}"
        )

@router.get("", response_model=List[BookingOut])
async def list_bookings():
    """List all bookings."""
    return await Booking.all()

@router.get("/{booking_id}", response_model=BookingOut)
async def get_booking(booking_id: int):
    """Retrieve a booking by its ID."""
    booking = await Booking.filter(id=booking_id).first()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    return booking

@router.delete("/{booking_id}")
async def delete_booking(booking_id: int, current_user: User = Depends(get_current_user)):
    """Delete a booking by its ID (only if it belongs to the current user)."""
    booking = await Booking.filter(id=booking_id, user_id=current_user.id).first()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found for the current user")
    await booking.delete()
    return {"detail": f"Booking ID {booking_id} cancelled"}

@router.post("", response_model=BookingOut)
async def schedule_booking(booking_in: BookingIn, current_user: User = Depends(get_current_user)):
    """Schedule a new booking for the authenticated user."""
    conflict = await Booking.filter(
        technician_name=booking_in.technician_name,
        booking_datetime=booking_in.booking_datetime,
    ).exists()
    if conflict:
        raise HTTPException(
            status_code=400,
            detail=f"Technician {booking_in.technician_name} is already booked at "
                   f"{booking_in.booking_datetime.strftime('%d/%m/%Y %I:%M%p')}",
        )
    booking = await Booking.create(
        technician_name=booking_in.technician_name,
        service=booking_in.service,
        booking_datetime=booking_in.booking_datetime,
        user=current_user,
    )
    return booking 