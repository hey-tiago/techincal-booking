"use client";

import React, {
  useState,
  useEffect,
  ChangeEvent,
  FormEvent,
  useRef,
} from "react";
import { useRouter } from "next/navigation";
import {
  AppBar,
  Box,
  Button,
  Container,
  CssBaseline,
  IconButton,
  Paper,
  TextField,
  Toolbar,
  Typography,
  List,
  ListItem,
  ListItemText,
  CircularProgress,
} from "@mui/material";
import SendIcon from "@mui/icons-material/Send";

interface ChatMessageDetails {
  id?: number;
  service?: string;
  technician?: string;
  datetime?: string;
}

interface ChatMessage {
  sender: string;
  text?: string;
  messageType: "text" | "booking_details" | "error";
  details?: ChatMessageDetails;
}

interface Booking {
  id: number;
  service: string;
  technician_name: string;
  booking_datetime: string;
}

const DashboardPage = () => {
  const router = useRouter();
  const [loading, setLoading] = useState(true);
  const [input, setInput] = useState<string>("");
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      sender: "System",
      text: "Hello! How can I help you today?",
      messageType: "text",
    },
  ]);
  const [bookings, setBookings] = useState<Booking[]>([]);
  const [showBookings, setShowBookings] = useState<boolean>(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Update safeGetToken to only use cookies
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
    console.log("storedToken", storedToken);
    if (!storedToken) {
      router.push("/");
      return;
    }
    setLoading(false);
  }, [router]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleSend = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    if (!input.trim()) return;

    const userMessage: ChatMessage = {
      sender: "User",
      text: input,
      messageType: "text",
    };
    setMessages((prev) => [...prev, userMessage]);

    try {
      const response = await fetch("http://localhost:8000/chat", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...(safeGetToken()
            ? { Authorization: `Bearer ${safeGetToken()}` }
            : {}),
        },
        body: JSON.stringify({ message: input }),
      });
      const data = await response.json();
      const systemMessage: ChatMessage = {
        sender: "System",
        text: data.response.text,
        messageType: data.response.message_type,
        details: data.response.details,
      };
      setMessages((prev) => [...prev, systemMessage]);
    } catch (error) {
      console.error("Error:", error);
      setMessages((prev) => [
        ...prev,
        {
          sender: "System",
          text: "Error processing request.",
          messageType: "error",
        },
      ]);
    }
    setInput("");
  };

  const handleInputChange = (e: ChangeEvent<HTMLInputElement>) => {
    setInput(e.target.value);
  };

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

  const renderChatMessage = (msg: ChatMessage, index: number) => {
    return (
      <Box key={index} mb={2}>
        <Typography
          variant="body1"
          color={msg.sender === "User" ? "primary" : "textSecondary"}
        >
          <strong>{msg.sender}:</strong> {msg.text}
        </Typography>
        {msg.messageType === "booking_details" && msg.details && (
          <Box sx={{ pl: 2, borderLeft: "2px solid #ccc", mt: 1 }}>
            <Typography variant="body2">
              <strong>Service ID:</strong> {msg.details.id}
            </Typography>
            <Typography variant="body2">
              <strong>Service:</strong> {msg.details.service}
            </Typography>
            <Typography variant="body2">
              <strong>Technician:</strong> {msg.details.technician}
            </Typography>
            <Typography variant="body2">
              <strong>Date/Time:</strong> {msg.details.datetime}
            </Typography>
          </Box>
        )}
      </Box>
    );
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
      <Container maxWidth="sm" sx={{ mt: 4 }}>
        <AppBar position="static">
          <Toolbar>
            <Typography variant="h6" sx={{ flexGrow: 1 }}>
              Technician Booking Chat
            </Typography>
            <Button color="inherit" onClick={handleShowBookings}>
              {showBookings ? "Hide My Bookings" : "Show My Bookings"}
            </Button>
            <Button color="inherit" onClick={handleLogout}>
              Logout
            </Button>
          </Toolbar>
        </AppBar>
        <Paper
          sx={{
            height: "60vh",
            display: "flex",
            flexDirection: "column",
            p: 2,
            mt: 2,
          }}
        >
          <Box sx={{ flexGrow: 1, overflowY: "auto", mb: 2 }}>
            {messages.map((msg, index) => renderChatMessage(msg, index))}
            <div ref={messagesEndRef} />
          </Box>
          <Box
            component="form"
            onSubmit={handleSend}
            sx={{ display: "flex", alignItems: "center" }}
          >
            <TextField
              fullWidth
              variant="outlined"
              placeholder="Type your message..."
              value={input}
              onChange={handleInputChange}
              InputProps={{
                endAdornment: (
                  <IconButton type="submit" color="primary">
                    <SendIcon />
                  </IconButton>
                ),
              }}
            />
          </Box>
        </Paper>
        {showBookings && (
          <Paper sx={{ mt: 4, p: 2 }}>
            <Typography variant="h6" gutterBottom>
              My Bookings
            </Typography>
            {bookings.length === 0 ? (
              <Typography>No bookings found.</Typography>
            ) : (
              <List>
                {bookings.map((booking) => (
                  <ListItem key={booking.id}>
                    <ListItemText
                      primary={`ID: ${booking.id} - ${booking.service}`}
                      secondary={`Technician: ${booking.technician_name} | Date/Time: ${booking.booking_datetime}`}
                    />
                  </ListItem>
                ))}
              </List>
            )}
          </Paper>
        )}
      </Container>
    </>
  );
};

export default DashboardPage;
