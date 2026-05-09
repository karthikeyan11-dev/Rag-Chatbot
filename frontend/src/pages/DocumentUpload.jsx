import React, { useState, useEffect, useRef } from "react";
import FileUpload from "../components/FileUpload";
import { getDocuments, getIngestionStatus, deleteDocument } from "../services/api";

export default function DocumentUpload() {
  const [documents, setDocuments] = useState([]);
  const [totalChunks, setTotalChunks] = useState(0);
  const [isLoading, setIsLoading] = useState(true);
  const [ingestionStatus, setIngestionStatus] = useState(null);
  const [deleteModal, setDeleteModal] = useState({ show: false, filename: null });
  const [isDeleting, setIsDeleting] = useState(false);
  const [statusMessage, setStatusMessage] = useState(null);
  const pollRef = useRef(null);

  const fetchDocuments = async () => {
    try {
      const data = await getDocuments();
      setDocuments(data.documents || []);
      setTotalChunks(data.total_chunks || 0);
    } catch (err) {
      console.error("Failed to fetch documents:", err);
    } finally {
      setIsLoading(false);
    }
  };

  const startPolling = () => {
    // Poll ingestion status every 2 seconds
    if (pollRef.current) clearInterval(pollRef.current);
    pollRef.current = setInterval(async () => {
      try {
        const status = await getIngestionStatus();
        setIngestionStatus(status);
        if (status.status === "complete" || status.status === "error") {
          clearInterval(pollRef.current);
          pollRef.current = null;
          // Refresh document list after ingestion completes
          fetchDocuments();
          // Auto-clear success status after 8 seconds
          if (status.status === "complete") {
            setTimeout(() => setIngestionStatus(null), 8000);
          }
        }
      } catch {
        // ignore polling errors
      }
    }, 2000);
  };

  const handleUploadSuccess = () => {
    fetchDocuments();
    setIngestionStatus({ status: "processing", message: "Processing documents... Generating embeddings." });
    startPolling();
  };

  const openDeleteModal = (filename) => {
    setStatusMessage(null); // Clear old messages
    setDeleteModal({ show: true, filename });
  };

  const closeDeleteModal = () => {
    if (isDeleting) return;
    setDeleteModal({ show: false, filename: null });
  };

  const confirmDelete = async () => {
    if (!deleteModal.filename || isDeleting) return;
    
    setIsDeleting(true);
    setStatusMessage(null);
    
    try {
      const result = await deleteDocument(deleteModal.filename);
      
      // Update local state immediately
      setDocuments(prev => prev.filter(doc => doc !== deleteModal.filename));
      
      setStatusMessage({
        type: "success",
        text: result.message || "Document deleted successfully."
      });
      
      // Close modal
      setDeleteModal({ show: false, filename: null });
      
      // Refresh chunk count from server
      fetchDocuments();
      
      // Clear status after 5 seconds
      setTimeout(() => setStatusMessage(null), 5000);
    } catch (err) {
      setStatusMessage({
        type: "error",
        text: err.message || "An error occurred while deleting the document."
      });
    } finally {
      setIsDeleting(false);
    }
  };

  useEffect(() => {
    fetchDocuments();
    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, []);

  return (
    <div className="flex-1 overflow-y-auto p-8 bg-slate-50 relative">
      {/* Confirmation Modal */}
      {deleteModal.show && (
        <div className="fixed inset-0 z-[100] flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-sm animate-fade-in">
          <div className="bg-white rounded-2xl shadow-2xl max-w-md w-full p-8 border border-slate-100">
            <div className="w-16 h-16 rounded-full bg-red-50 flex items-center justify-center mb-6 mx-auto">
              <svg className="w-8 h-8 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
              </svg>
            </div>
            <h3 className="text-xl font-bold text-slate-800 text-center mb-3">Confirm Deletion</h3>
            <p className="text-slate-500 text-center mb-8">
              Are you sure you want to delete <span className="font-semibold text-slate-700">"{deleteModal.filename}"</span>? This will permanently remove the document and all related embeddings from the AI knowledge base.
            </p>
            <div className="flex gap-3">
              <button
                onClick={closeDeleteModal}
                disabled={isDeleting}
                className="flex-1 px-6 py-3 rounded-xl border border-slate-200 text-slate-600 font-medium hover:bg-slate-50 transition-colors disabled:opacity-50"
              >
                Cancel
              </button>
              <button
                onClick={confirmDelete}
                disabled={isDeleting}
                className="flex-1 px-6 py-3 rounded-xl bg-red-600 text-white font-medium hover:bg-red-700 transition-colors shadow-lg shadow-red-200 disabled:opacity-50 flex items-center justify-center gap-2"
              >
                {isDeleting ? (
                  <>
                    <svg className="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                    </svg>
                    Deleting...
                  </>
                ) : (
                  "Delete"
                )}
              </button>
            </div>
          </div>
        </div>
      )}

      <div className="max-w-4xl mx-auto space-y-10">
        {/* Status Messages (Toasts) */}
        {statusMessage && (
          <div className={`fixed bottom-8 left-1/2 -translate-x-1/2 z-[90] rounded-2xl px-6 py-4 flex items-center gap-3 shadow-2xl animate-fade-in border ${
            statusMessage.type === "success" ? "bg-white text-green-800 border-green-100" : "bg-white text-red-800 border-red-100"
          }`}>
            {statusMessage.type === "success" ? (
              <svg className="w-5 h-5 text-green-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            ) : (
              <svg className="w-5 h-5 text-red-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
              </svg>
            )}
            <span className="font-semibold">{statusMessage.text}</span>
            <button onClick={() => setStatusMessage(null)} className="ml-4 text-slate-400 hover:text-slate-600 text-xl leading-none">×</button>
          </div>
        )}

        {/* Ingestion Status Banner */}
        {ingestionStatus && (
          <div className={`rounded-xl px-5 py-4 flex items-center gap-3 text-sm font-medium shadow-sm transition-all duration-300 ${
            ingestionStatus.status === "processing"
              ? "bg-blue-50 border border-blue-200 text-blue-800"
              : ingestionStatus.status === "complete"
              ? "bg-green-50 border border-green-200 text-green-800"
              : "bg-red-50 border border-red-200 text-red-800"
          }`}>
            {ingestionStatus.status === "processing" ? (
              <svg className="w-5 h-5 animate-spin text-blue-600 flex-shrink-0" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
              </svg>
            ) : ingestionStatus.status === "complete" ? (
              <svg className="w-5 h-5 text-green-600 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            ) : (
              <svg className="w-5 h-5 text-red-600 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
              </svg>
            )}
            <div>
              <p>{ingestionStatus.message}</p>
              {ingestionStatus.status === "processing" && (
                <p className="text-xs opacity-70 mt-0.5">This may take a minute depending on document size.</p>
              )}
            </div>
          </div>
        )}

        <section>
          <div className="mb-6">
            <h2 className="text-2xl font-bold text-slate-800">Upload Knowledge Base</h2>
            <p className="text-slate-500">Add new PDF documents to the RAG pipeline. They will be automatically processed and available for chat.</p>
          </div>
          <FileUpload onUploadSuccess={handleUploadSuccess} />
        </section>

        <section>
          <div className="flex items-center justify-between mb-6 border-b border-slate-200 pb-4">
            <h3 className="text-lg font-semibold text-slate-800 flex items-center gap-2">
              <svg className="w-5 h-5 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
              </svg>
              Uploaded Documents ({documents.length})
            </h3>
            {totalChunks > 0 && (
              <span className="text-xs font-medium text-slate-400 bg-slate-100 px-3 py-1 rounded-full">
                {totalChunks} chunks indexed
              </span>
            )}
          </div>

          {isLoading ? (
            <div className="flex justify-center py-10">
              <div className="w-8 h-8 border-4 border-blue-600 border-t-transparent rounded-full animate-spin"></div>
            </div>
          ) : documents.length > 0 ? (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {documents.map((doc, idx) => (
                <div key={idx} className="flex items-center gap-3 p-4 bg-white border border-slate-200 rounded-2xl shadow-sm hover:shadow-md transition-all group">
                  <div className="w-10 h-10 rounded-xl bg-blue-50 flex items-center justify-center flex-shrink-0 group-hover:bg-blue-100 transition-colors">
                    <svg className="w-6 h-6 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z" />
                    </svg>
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-semibold text-slate-800 truncate">{doc}</p>
                    <p className="text-[10px] text-slate-400 uppercase font-bold tracking-wider">PDF Document</p>
                  </div>
                  <button
                    onClick={() => openDeleteModal(doc)}
                    className="p-2.5 text-slate-300 hover:text-red-500 hover:bg-red-50 rounded-xl transition-all duration-200"
                    title="Delete Document"
                  >
                    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                    </svg>
                  </button>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-center py-20 bg-white border border-slate-200 border-dashed rounded-2xl">
              <svg className="w-12 h-12 text-slate-300 mx-auto mb-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.5" d="M9 13h6m-3-3v6m5 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
              <p className="text-slate-400 font-medium">No documents uploaded yet.</p>
              <p className="text-slate-400 text-sm mt-1">Upload company PDFs above to get started.</p>
            </div>
          )}
        </section>
      </div>
    </div>
  );
}
