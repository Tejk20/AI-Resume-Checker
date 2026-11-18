import { useState, useEffect, useCallback } from "react";
import { errorMessage } from "../services/api";
export function useLoad(loader, deps = []) {
  const [data, setData] = useState(null),
    [error, setError] = useState(""),
    [loading, setLoading] = useState(true),
    [revision, setRevision] = useState(0);
  useEffect(() => {
    let alive = true;
    setLoading(true);
    setError("");
    Promise.resolve()
      .then(loader)
      .then((v) => {
        if (alive) setData(v);
      })
      .catch((e) => {
        if (alive) setError(errorMessage(e));
      })
      .finally(() => {
        if (alive) setLoading(false);
      });
    return () => {
      alive = false;
    };
  }, [...deps, revision]);
  return {
    data,
    error,
    loading,
    reload: useCallback(() => setRevision((x) => x + 1), []),
  };
}
