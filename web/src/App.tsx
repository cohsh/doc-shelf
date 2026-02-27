import { Navigate, Route, Routes } from "react-router-dom";
import Layout from "./components/Layout";
import DocumentDetailPage from "./pages/DocumentDetailPage";
import LibraryPage from "./pages/LibraryPage";
import UploadPage from "./pages/UploadPage";

export default function App() {
  return (
    <Layout>
      <Routes>
        <Route path="/" element={<Navigate to="/library" replace />} />
        <Route path="/library" element={<LibraryPage />} />
        <Route path="/documents/:id" element={<DocumentDetailPage />} />
        <Route path="/upload" element={<UploadPage />} />
      </Routes>
    </Layout>
  );
}
