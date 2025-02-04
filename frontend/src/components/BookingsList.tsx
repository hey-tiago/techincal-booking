"use client";

import React from "react";
import { Paper, Typography, List, ListItem, ListItemText } from "@mui/material";

interface Booking {
  id: number;
  service: string;
  technician_name: string;
  booking_datetime: string;
}

interface BookingsListProps {
  bookings: Booking[];
}

const BookingsList: React.FC<BookingsListProps> = ({ bookings }) => {
  return (
    <Paper
      elevation={3}
      sx={{
        p: 3,
        borderRadius: 1,
        backgroundColor: "white",
      }}
    >
      <Typography variant="h6" gutterBottom sx={{ color: "#111827", mb: 2 }}>
        My Bookings
      </Typography>
      {bookings.length === 0 ? (
        <Typography sx={{ color: "#6B7280" }}>No bookings found.</Typography>
      ) : (
        <List sx={{ p: 0 }}>
          {bookings.map((booking) => (
            <ListItem
              key={booking.id}
              sx={{
                borderBottom: "1px solid #E5E7EB",
                "&:last-child": {
                  borderBottom: "none",
                },
              }}
            >
              <ListItemText
                primary={
                  <Typography sx={{ color: "#111827", fontWeight: 500 }}>
                    {`ID: ${booking.id} - ${booking.service}`}
                  </Typography>
                }
                secondary={
                  <Typography
                    variant="body2"
                    sx={{ color: "#6B7280", mt: 0.5 }}
                  >
                    {`Technician: ${booking.technician_name} | Date/Time: ${booking.booking_datetime}`}
                  </Typography>
                }
              />
            </ListItem>
          ))}
        </List>
      )}
    </Paper>
  );
};

export default BookingsList;
