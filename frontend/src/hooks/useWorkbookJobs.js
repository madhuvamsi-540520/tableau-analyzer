import { useCallback, useEffect, useState } from "react";
import { App as AntApp } from "antd";
import { api } from "../api/client.js";

// Shared workbook-job state: upload, list, select, load detail, delete.
// Jobs are session-scoped on the backend and thus shared across tabs.
export function useWorkbookJobs() {
  const { message } = AntApp.useApp();
  const [jobs, setJobs] = useState([]);
  const [errors, setErrors] = useState([]);
  const [busy, setBusy] = useState(false);
  const [loading, setLoading] = useState(true);
  const [selectedId, setSelectedId] = useState(null);
  const [detail, setDetail] = useState(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [detailError, setDetailError] = useState(null);

  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      const data = await api.listJobs();
      setJobs(data.jobs || []);
      return data.jobs || [];
    } catch (e) {
      message.error(e.message || "Could not load workbooks.");
      return [];
    } finally {
      setLoading(false);
    }
  }, [message]);

  const select = useCallback(async (jobId) => {
    setSelectedId(jobId);
    setDetail(null);
    setDetailError(null);
    setDetailLoading(true);
    try {
      const data = await api.getJob(jobId);
      setDetail(data.metadata || null);
    } catch (e) {
      setDetailError(e.message || "Could not load workbook metadata.");
    } finally {
      setDetailLoading(false);
    }
  }, []);

  const upload = useCallback(
    async (files) => {
      setBusy(true);
      setErrors([]);
      try {
        const res = await api.upload(files);
        const ok = (res.jobs || []).filter((j) => j.ok);
        const bad = (res.jobs || []).filter((j) => !j.ok);
        setErrors(bad);
        if (ok.length) message.success(`Analyzed ${ok.length} workbook(s).`);
        if (bad.length) message.warning(`${bad.length} file(s) could not be processed.`);
        await refresh();
        if (ok.length) select(ok[0].jobId);
      } catch (e) {
        message.error(e.message || "Upload failed.");
      } finally {
        setBusy(false);
      }
    },
    [message, refresh, select]
  );

  const remove = useCallback(
    async (jobId) => {
      try {
        await api.deleteJob(jobId);
        if (jobId === selectedId) {
          setSelectedId(null);
          setDetail(null);
        }
        message.success("Removed.");
        await refresh();
      } catch (e) {
        message.error(e.message || "Delete failed.");
      }
    },
    [message, refresh, selectedId]
  );

  useEffect(() => {
    refresh();
  }, [refresh]);

  return {
    jobs, errors, setErrors, busy, loading,
    selectedId, detail, detailLoading, detailError,
    refresh, select, upload, remove,
  };
}
