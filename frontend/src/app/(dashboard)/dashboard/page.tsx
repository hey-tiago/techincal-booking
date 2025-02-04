"use client";

import React, { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import {
  AppBar,
  Box,
  Button,
  Container,
  CssBaseline,
  Toolbar,
  Typography,
  CircularProgress,
} from "@mui/material";
import Chat from "@/components/Chat";
import BookingsList from "@/components/BookingsList";

interface Booking {
  id: number;
  service: string;
  technician_name: string;
  booking_datetime: string;
}

const DashboardPage = () => {
  const router = useRouter();
  const [loading, setLoading] = useState(true);
  const [bookings, setBookings] = useState<Booking[]>([]);
  const [showBookings, setShowBookings] = useState<boolean>(false);

  const safeGetToken = (): string | null => {
    try {
      if (typeof window === "undefined") return null;
      const cookies = document.cookie.split(";");
      const tokenCookie = cookies.find((cookie) =>
        cookie.trim().startsWith("token=")
      );
      return tokenCookie ? tokenCookie.split("=")[1] : null;
    } catch (err) {
      console.error("Error accessing cookies:", err);
      return null;
    }
  };

  useEffect(() => {
    const storedToken = safeGetToken();
    if (!storedToken) {
      router.push("/");
      return;
    }
    setLoading(false);
  }, [router]);

  const fetchMyBookings = async () => {
    if (!safeGetToken()) return;
    try {
      const response = await fetch("http://localhost:8000/my-bookings", {
        method: "GET",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${safeGetToken()}`,
        },
      });
      if (!response.ok) {
        alert("Failed to fetch bookings.");
        return;
      }
      const data = await response.json();
      setBookings(data);
    } catch (error) {
      console.error("Fetch bookings error:", error);
      alert("Error fetching bookings.");
    }
  };

  const handleShowBookings = async () => {
    await fetchMyBookings();
    setShowBookings(!showBookings);
  };

  const handleLogout = () => {
    document.cookie = "token=; path=/; expires=Thu, 01 Jan 1970 00:00:00 GMT";
    router.push("/");
  };

  if (loading) {
    return (
      <Box
        display="flex"
        justifyContent="center"
        alignItems="center"
        minHeight="100vh"
      >
        <CircularProgress />
      </Box>
    );
  }

  return (
    <>
      <CssBaseline />
      <Box sx={{ backgroundColor: "#F3F4F6", minHeight: "100vh" }}>
        <AppBar
          position="static"
          sx={{ backgroundColor: "white", boxShadow: 1 }}
        >
          <Toolbar>
            <Typography variant="h6" sx={{ flexGrow: 1, color: "#111827" }}>
              Dashboard
            </Typography>
            <Button
              color="inherit"
              onClick={handleShowBookings}
              sx={{ color: "#374151" }}
            >
              {showBookings ? "Hide My Bookings" : "Show My Bookings"}
            </Button>
            <Button
              color="inherit"
              onClick={handleLogout}
              sx={{ color: "#374151" }}
            >
              Logout
            </Button>
          </Toolbar>
        </AppBar>

        <Container
          maxWidth="md"
          sx={{
            mt: 4,
            mb: 4,
            display: "flex",
            flexDirection: "column",
            gap: 3,
          }}
        >
          <Chat getToken={safeGetToken} />
          {showBookings && <BookingsList bookings={bookings} />}
        </Container>
      </Box>
    </>
  );
};

export default DashboardPage;
