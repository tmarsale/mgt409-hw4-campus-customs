import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import App from "./App";
import { AssistantResultsProvider } from "./assistantResults";
import { AuthProvider } from "./auth";
import "./index.css";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <BrowserRouter>
      <AuthProvider>
        <AssistantResultsProvider>
          <App />
        </AssistantResultsProvider>
      </AuthProvider>
    </BrowserRouter>
  </StrictMode>,
);
