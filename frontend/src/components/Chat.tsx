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
  TextField,
  Typography,
  IconButton,
  Paper,
  Button,
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

interface ChatProps {
  getToken: () => string | null;
}

const Chat: React.FC<ChatProps> = ({ getToken }) => {
  const [input, setInput] = useState<string>("");
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      sender: "System",
      text: "Hello! How can I help you today?",
      messageType: "text",
    },
  ]);
  const messagesEndRef = useRef<HTMLDivElement>(null);

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
          ...(getToken() ? { Authorization: `Bearer ${getToken()}` } : {}),
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

  const renderChatMessage = (msg: ChatMessage, index: number) => {
    const isUser = msg.sender === "User";
    return (
      <Box
        key={index}
        sx={{
          display: "flex",
          justifyContent: isUser ? "flex-end" : "flex-start",
          mb: 1,
        }}
      >
        <Box
          sx={{
            maxWidth: "70%",
            backgroundColor: isUser ? "#0B57D0" : "#F3F4F6",
            borderRadius: "16px",
            px: 2,
            py: 1,
            color: isUser ? "white" : "inherit",
          }}
        >
          <Typography variant="body1">{msg.text}</Typography>
          {msg.messageType === "booking_details" && msg.details && (
            <Box sx={{ mt: 1 }}>
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
      </Box>
    );
  };

  return (
    <Paper
      elevation={3}
      sx={{
        borderRadius: 1,
        overflow: "hidden",
      }}
    >
      {/* Header */}
      <Box
        sx={{
          p: 2,
          borderBottom: "1px solid #E5E7EB",
          backgroundColor: "white",
        }}
      >
        <Typography variant="h6" sx={{ color: "#111827", fontSize: "1.3rem" }}>
          Technician scheduling support
        </Typography>
        <Typography
          variant="body2"
          sx={{ color: "#6B7280", fontSize: "0.875rem" }}
        >
          We typically reply within a few minutes
        </Typography>
      </Box>

      {/* Chat Messages */}
      <Box
        sx={{
          height: "400px",
          backgroundColor: "#FaFaFa",
          overflowY: "auto",
          p: 2,
        }}
      >
        {messages.map((msg, index) => renderChatMessage(msg, index))}
        <div ref={messagesEndRef} />
      </Box>

      {/* Input Area */}
      <Box
        component="form"
        onSubmit={handleSend}
        sx={{
          p: 2,
          backgroundColor: "white",
          borderTop: "1px solid #E5E7EB",
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
        }}
      >
        <TextField
          fullWidth
          placeholder="Type your message..."
          value={input}
          onChange={handleInputChange}
          variant="outlined"
          size="small"
          sx={{
            "& .MuiOutlinedInput-root": {
              borderRadius: "8px",
              backgroundColor: "#FFF",
              "&.Mui-focused fieldset": {
                borderColor: "#0B57D0",
              },
            },
          }}
        />
        <Button
          type="submit"
          color="primary"
          title={input.trim() ? "Send message" : "Please type a message first"}
          sx={{
            marginLeft: 1,
            minWidth: "40px",
            width: "40px",
            padding: "6px",
            borderRadius: "8px",
            backgroundColor: input.trim() ? "#0B57D0" : "transparent",
            color: input.trim() ? "white" : "#9CA3AF",
            "&:hover": {
              backgroundColor: input.trim() ? "#0842A0" : "transparent",
            },
            cursor: input.trim() ? "pointer" : "not-allowed",
          }}
        >
          <SendIcon
            sx={{
              width: "25px",
              marginBottom: "4px",
              marginLeft: "4px",
              transform: "rotate(-45deg)",
            }}
          />
        </Button>
      </Box>
    </Paper>
  );
};

export default Chat;
