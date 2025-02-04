"use client";

import React, {
  useState,
  useEffect,
  ChangeEvent,
  FormEvent,
  useRef,
} from "react";
import {
  Box,
  Container,
  CssBaseline,
  IconButton,
  Paper,
  TextField,
  Typography,
} from "@mui/material";
import SendIcon from "@mui/icons-material/Send";

interface MessageDetails {
  id?: number;
  service?: string;
  technician?: string;
  datetime?: string;
}

interface Message {
  sender: string;
  text?: string;
  messageType: "text" | "booking_details" | "error";
  details?: MessageDetails;
}

const Home: React.FC = () => {
  const [input, setInput] = useState<string>("");
  const [messages, setMessages] = useState<Message[]>([
    {
      sender: "System",
      text: "Hello! How can I help you today?",
      messageType: "text",
    },
  ]);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Scroll to the bottom of the chat whenever messages update
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleSend = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    if (!input.trim()) return;

    const userMessage: Message = {
      sender: "User",
      text: input,
      messageType: "text",
    };
    setMessages((prev) => [...prev, userMessage]);

    try {
      const response = await fetch("http://localhost:8000/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: input }),
      });
      const data = await response.json();
      const systemMessage: Message = {
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

  const renderMessageContent = (msg: Message) => {
    if (msg.messageType === "booking_details" && msg.details) {
      return (
        <>
          {msg.text && (
            <Typography
              variant="body1"
              gutterBottom
              sx={{
                fontWeight: 500,
                color: "#1a73e8",
                mb: 2,
              }}
            >
              {msg.text}
            </Typography>
          )}
          <Box
            sx={{
              backgroundColor: "white",
              p: 3,
              m: -2,
              borderRadius: 1,
              border: "1px solid #e8eaed",
            }}
          >
            <Typography
              variant="body1"
              sx={{
                display: "flex",
                alignItems: "center",
                gap: 1,
                mb: 1,
              }}
            >
              <span style={{ fontWeight: 500 }}>Service ID:</span>{" "}
              {msg.details.id}
            </Typography>
            <Typography
              variant="body1"
              sx={{
                display: "flex",
                alignItems: "center",
                gap: 1,
                mb: 1,
              }}
            >
              <span style={{ fontWeight: 500 }}>Service:</span>{" "}
              {msg.details.service}
            </Typography>
            <Typography
              variant="body1"
              sx={{
                display: "flex",
                alignItems: "center",
                gap: 1,
                mb: 1,
              }}
            >
              <span style={{ fontWeight: 500 }}>Technician:</span>{" "}
              {msg.details.technician}
            </Typography>
            <Typography
              variant="body1"
              sx={{
                display: "flex",
                alignItems: "center",
                gap: 1,
              }}
            >
              <span style={{ fontWeight: 500 }}>Date/Time:</span>{" "}
              {msg.details.datetime}
            </Typography>
          </Box>
        </>
      );
    }
    return <Typography variant="body1">{msg.text}</Typography>;
  };

  const renderMessage = (msg: Message, index: number) => {
    const isUser = msg.sender === "User";
    return (
      <Box
        key={index}
        display="flex"
        flexDirection="row"
        justifyContent={isUser ? "flex-end" : "flex-start"}
        mb={2}
      >
        <Paper
          elevation={0}
          sx={{
            p: 2,
            maxWidth: "70%",
            backgroundColor: isUser ? "#0B57D0" : "#F3F6FC",
            color: isUser ? "white" : "black",
            borderRadius: 2,
          }}
        >
          {renderMessageContent(msg)}
        </Paper>
      </Box>
    );
  };

  return (
    <CssBaseline>
      <Container maxWidth="sm" sx={{ mt: 4, mb: 4 }}>
        <Paper
          elevation={1}
          sx={{
            borderRadius: 2,
            overflow: "hidden",
          }}
        >
          {/* Header */}
          <Box sx={{ p: 2, borderBottom: "1px solid #E0E0E0" }}>
            <Typography
              variant="h6"
              color="text.secondary"
              sx={{ fontSize: "1rem", fontWeight: "bold" }}
            >
              Technician scheduling support
            </Typography>
            <Typography
              variant="body2"
              color="text.secondary"
              sx={{ fontSize: "0.875rem" }}
            >
              We typically reply within a few minutes
            </Typography>
          </Box>

          {/* Messages Area */}
          <Box
            sx={{
              height: "50vh",
              overflowY: "auto",
              p: 2,
              backgroundColor: "#f9f9f9",
            }}
          >
            {messages.map((msg, index) => renderMessage(msg, index))}
            <div ref={messagesEndRef} />
          </Box>

          {/* Input Area */}
          <Box
            component="form"
            onSubmit={handleSend}
            sx={{
              p: 2,
              borderTop: "1px solid #E0E0E0",
              backgroundColor: "white",
            }}
          >
            <TextField
              fullWidth
              variant="outlined"
              placeholder="Type your message..."
              value={input}
              onChange={handleInputChange}
              sx={{
                "& .MuiOutlinedInput-root": {
                  borderRadius: "24px",
                  backgroundColor: "#F3F6FC",
                  "& fieldset": {
                    borderColor: "transparent",
                  },
                  "&:hover fieldset": {
                    borderColor: "transparent",
                  },
                  "&.Mui-focused fieldset": {
                    borderColor: "transparent",
                  },
                },
              }}
              InputProps={{
                endAdornment: (
                  <IconButton
                    type="submit"
                    color="primary"
                    sx={{ color: "#0B57D0" }}
                  >
                    <SendIcon />
                  </IconButton>
                ),
              }}
            />
          </Box>
        </Paper>
      </Container>
    </CssBaseline>
  );
};

export default Home;
