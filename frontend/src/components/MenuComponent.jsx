import React, { useEffect, useState } from 'react'
import { AlertTriangle, CheckCircle, Clock, FileText, Upload } from 'lucide-react'
import api from '../utils/api.util'

function MenuComponent() {

    const [documents, setDocuments] = useState([]);
    const [selectedFile, setSelectedFile] = useState(null);
    const [uploading, setUploading] = useState(false);
    const [uploadStatus, setUploadStatus] = useState('');

    const fetchDocs = async () => {
        try {
            const res = await api.get('/retriveAllDocuments');
            setDocuments(res.data.files || []);
        } catch (err) {
            console.error("Failed to fetch documents", err);
        }
    };

    const handleFileChange = (e) => {
        const file = e.target.files?.[0];
        setSelectedFile(file || null);
        setUploadStatus('');
    };

    const pollJobStatus = async (jobId) => {
        // Simple polling loop for background audit completion
        const maxAttempts = 300;
        const delay = (ms) => new Promise((r) => setTimeout(r, ms));

        for (let attempt = 0; attempt < maxAttempts; attempt++) {
            try {
                const res = await api.get(`/job-status/${jobId}`);
                const status = res.data?.status;
                if (status === 'completed') {
                    setUploadStatus('File processed successfully.');
                    await fetchDocs();
                    return;
                }
                if (status === 'failed' || status === 'not_found') {
                    setUploadStatus('File processing failed.');
                    return;
                }
            } catch {
                setUploadStatus('Error while checking job status.');
                return;
            }
            await delay(2000);
        }
        setUploadStatus('Processing is taking longer than expected. Please refresh later.');
    };

    const handleUpload = async () => {
        if (!selectedFile || uploading) return;

        const formData = new FormData();
        formData.append('file', selectedFile);

        try {
            setUploading(true);
            setUploadStatus('Uploading file...');

            const res = await api.post('/upload', formData, {
                headers: { 'Content-Type': 'multipart/form-data' },
            });

            const jobId = res.data?.job_id;
            if (jobId) {
                setUploadStatus('Upload successful. Auditing file...');
                await pollJobStatus(jobId);
            } else {
                setUploadStatus('Upload successful.');
                await fetchDocs();
            }
        } catch (err) {
            console.error('Upload failed', err);
            setUploadStatus('Upload failed.');
        } finally {
            setUploading(false);
        }
    };

    useEffect(() => {
        fetchDocs();
    }, []);

    return (
        <div className="flex h-screen bg-gray-50">
            {/* SIDEBAR: The Knowledge Base */}
            <div className="w-64 bg-white border-r flex flex-col">
                <div className="p-4 border-b flex flex-col gap-3">
                    <div className="font-bold text-lg flex items-center gap-2">
                        <Clock size={20} /> Knowledge Base
                    </div>
                    <div className="flex items-center gap-2">
                        <label className="flex-1">
                            <span className="sr-only">Upload document</span>
                            <input
                                type="file"
                                className="block w-full text-xs text-gray-600
                                           file:mr-3 file:py-1.5 file:px-3
                                           file:rounded-full file:border-0
                                           file:text-xs file:font-semibold
                                           file:bg-blue-50 file:text-blue-700
                                           hover:file:bg-blue-100"
                                onChange={handleFileChange}
                                disabled={uploading}
                            />
                        </label>
                        <button
                            type="button"
                            onClick={handleUpload}
                            disabled={!selectedFile || uploading}
                            className="inline-flex items-center gap-1 px-3 py-1.5 rounded-full text-xs font-semibold text-white bg-blue-600 hover:bg-blue-700 disabled:opacity-60 disabled:cursor-not-allowed"
                        >
                            <Upload size={14} />
                            {uploading ? 'Uploading...' : 'Upload'}
                        </button>
                    </div>
                    {uploadStatus && (
                        <p className="text-[11px] text-gray-500">
                            {uploadStatus}
                        </p>
                    )}
                </div>
                <div className="flex-1 overflow-y-auto p-2 space-y-2">

                    {(!documents || documents.length === 0) && (
                        <div className="text-center text-xs text-gray-400 py-4">No documents available.</div>
                    )}
                    {documents?.map((doc, i) => (
                        <div key={i} className="p-3 rounded-lg border bg-gray-50 flex flex-col gap-1">
                            <div className="flex items-center justify-between">
                                <span className="text-sm font-medium truncate w-40">{doc.name}</span>
                                {doc.status === 'verified' ? (
                                    <CheckCircle size={16} className="text-green-500" />
                                ) : doc.status === 'conflict' ? (
                                    <AlertTriangle size={16} className="text-red-500" />
                                ) : (
                                    <FileText size={16} className="text-blue-500" />
                                )}
                            </div>
                            <span className="text-[10px] text-gray-500">{doc.time}</span>
                        </div>
                    ))}
                </div>
            </div>
        </div>
    )
}

export default MenuComponent