import { Routes, Route } from "react-router-dom";
import Navbar from "./components/Navbar";
import Home from "./pages/Home";
import Chat from "./pages/Chat";
import Login from "./pages/Login";
import Register from "./pages/Register";
import Sobre from "./pages/Sobre";

export default function App() {
  return (
    <div className="flex flex-col min-h-screen">
      <Navbar />
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/chat" element={<Chat />} />
        <Route path="/login" element={<Login />} />
        <Route path="/register" element={<Register />} />
        <Route path="/sobre" element={<Sobre />} />
      </Routes>
    </div>
  );
}









