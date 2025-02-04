"use client";

import React, {
  useState,
  useEffect,
  ChangeEvent,
  FormEvent,
  useRef,
} from "react";
import {
  AppBar,
  Box,
  Container,
  CssBaseline,
  IconButton,
  InputAdornment,
  Paper,
  TextField,
  Toolbar,
  Typography,
  Avatar,
} from "@mui/material";
import SendIcon from "@mui/icons-material/Send";

interface Message {
  sender: string;
  text: string;
}

const Home: React.FC = () => {
  const [input, setInput] = useState<string>("");
  const [messages, setMessages] = useState<Message[]>([]);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Scroll to the bottom of the chat whenever messages update
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleSend = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    if (!input.trim()) return;

    // Add user's message to the chat history.
    const userMessage: Message = { sender: "User", text: input };
    setMessages((prev) => [...prev, userMessage]);

    try {
      // Send the message to the backend /chat endpoint.
      const response = await fetch("http://localhost:8000/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: input }),
      });
      const data = await response.json();

      const systemMessage: Message = { sender: "System", text: data.response };
      setMessages((prev) => [...prev, systemMessage]);
    } catch (error) {
      console.error("Error:", error);
      setMessages((prev) => [
        ...prev,
        { sender: "System", text: "Error processing request." },
      ]);
    }
    setInput("");
  };

  const handleInputChange = (e: ChangeEvent<HTMLInputElement>) => {
    setInput(e.target.value);
  };

  // Render chat bubbles with different styles for User and System messages.
  const renderMessage = (msg: Message, index: number) => {
    const isUser = msg.sender === "User";
    return (
      <Box
        key={index}
        display="flex"
        flexDirection="row"
        justifyContent={isUser ? "flex-end" : "flex-start"}
        mb={1}
      >
        {!isUser && (
          <Avatar
            sx={{ bgcolor: "primary.main", mr: 1, width: 32, height: 32 }}
          >
            S
          </Avatar>
        )}
        <Paper
          elevation={3}
          sx={{
            p: 1.5,
            maxWidth: "70%",
            backgroundColor: isUser ? "primary.light" : "grey.200",
            color: isUser ? "primary.contrastText" : "text.primary",
            borderRadius: 2,
            wordWrap: "break-word",
          }}
        >
          <Typography variant="body1">{msg.text}</Typography>
        </Paper>
        {isUser && (
          <Avatar
            sx={{ bgcolor: "secondary.main", ml: 1, width: 32, height: 32 }}
          >
            U
          </Avatar>
        )}
      </Box>
    );
  };

  return (
    <>
      <CssBaseline />
      <AppBar position="static">
        <Toolbar>
          <Typography variant="h6" component="div">
            Technician Booking Chat
          </Typography>
        </Toolbar>
      </AppBar>
      <Container maxWidth="sm" sx={{ mt: 4, mb: 4 }}>
        <Paper
          sx={{
            height: "60vh",
            display: "flex",
            flexDirection: "column",
            p: 2,
            borderRadius: 2,
          }}
        >
          <Box
            sx={{
              flexGrow: 1,
              overflowY: "auto",
              mb: 2,
              px: 1,
            }}
          >
            {messages.map((msg, index) => renderMessage(msg, index))}
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
                  <InputAdornment position="end">
                    <IconButton type="submit" color="primary">
                      <SendIcon />
                    </IconButton>
                  </InputAdornment>
                ),
              }}
            />
          </Box>
        </Paper>
      </Container>
    </>
  );
};

export default Home;
