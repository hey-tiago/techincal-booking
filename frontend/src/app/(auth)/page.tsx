"use client";

import React, { useState, FormEvent, useEffect } from "react";
import { useRouter } from "next/navigation";
import {
  Box,
  Button,
  Container,
  CssBaseline,
  Paper,
  TextField,
  Typography,
  CircularProgress,
} from "@mui/material";

const AuthPage = () => {
  const router = useRouter();
  const [authMode, setAuthMode] = useState<"login" | "signup">("login");
  const [username, setUsername] = useState<string>("");
  const [password, setPassword] = useState<string>("");
  const [loading, setLoading] = useState(true);

  // Helper function to safely access cookies
  const safeGetToken = () => {
    if (typeof window === "undefined") return null;
    try {
      // Check cookie instead of localStorage
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
    const token = safeGetToken();
    if (token) {
      router.push("/dashboard");
      return;
    }
    setLoading(false);
  }, [router]);

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

  const handleAuthSubmit = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    if (authMode === "signup") {
      try {
        const response = await fetch("http://localhost:8000/signup", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ username, password }),
        });
        if (!response.ok) {
          const errorData = await response.json();
          alert("Sign up failed: " + errorData.detail);
          return;
        }
        alert("Sign up successful! Please log in.");
        setAuthMode("login");
      } catch (error) {
        console.error("Signup error:", error);
        alert("Signup error.");
      }
    } else {
      try {
        const formData = new URLSearchParams();
        formData.append("username", username);
        formData.append("password", password);
        const response = await fetch("http://localhost:8000/login", {
          method: "POST",
          headers: { "Content-Type": "application/x-www-form-urlencoded" },
          body: formData.toString(),
        });
        if (!response.ok) {
          const errorData = await response.json();
          alert("Login failed: " + errorData.detail);
          return;
        }
        const data = await response.json();

        // Set cookie only (remove localStorage)
        document.cookie = `token=${data.access_token}; path=/`;

        router.push("/dashboard");
      } catch (error) {
        console.error("Login error:", error);
        alert("Login error.");
      }
    }
  };

  const handleLogout = () => {
    localStorage.removeItem("token");
    document.cookie = "token=; path=/; expires=Thu, 01 Jan 1970 00:00:00 GMT";
    router.push("/");
  };

  return (
    <>
      <CssBaseline />
      <Container maxWidth="sm" sx={{ mt: 4 }}>
        <Paper sx={{ p: 4 }}>
          <Typography variant="h5" align="center" gutterBottom>
            {authMode === "login" ? "Login" : "Sign Up"}
          </Typography>
          <Box
            component="form"
            onSubmit={handleAuthSubmit}
            sx={{ display: "flex", flexDirection: "column", gap: 2 }}
          >
            <TextField
              label="Username"
              variant="outlined"
              fullWidth
              value={username}
              onChange={(e) => setUsername(e.target.value)}
            />
            <TextField
              label="Password"
              variant="outlined"
              type="password"
              fullWidth
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
            <Button type="submit" variant="contained" color="primary">
              {authMode === "login" ? "Login" : "Sign Up"}
            </Button>
          </Box>
          <Box mt={2} textAlign="center">
            <Button
              onClick={() =>
                setAuthMode(authMode === "login" ? "signup" : "login")
              }
            >
              {authMode === "login"
                ? "Don't have an account? Sign Up"
                : "Already have an account? Login"}
            </Button>
          </Box>
        </Paper>
      </Container>
    </>
  );
};

export default AuthPage;
