import axios from "axios";
import type {CatalogFile, IngestionRun, QueryCatalogEntry} from "./types";

const api = axios.create({baseURL: "/api/v1", timeout: 120000});

export async function getFiles(): Promise<CatalogFile[]> { return (await api.get("/catalog/files")).data.files; }
export async function getSchema() { return (await api.get("/catalog/schema")).data; }
export async function getQueries(): Promise<QueryCatalogEntry[]> { return (await api.get("/catalog/queries")).data; }
export async function validateFiles(files?: string[]) { return (await api.post("/ingestion/validate", {files: files?.length ? files : null})).data; }
export async function startRun(files: string[] | undefined, skipUnchanged: boolean, batchSize: number) {
  return (await api.post("/ingestion/runs", {files: files?.length ? files : null, skip_unchanged: skipUnchanged, batch_size: batchSize, mode: "LOAD"})).data;
}
export async function getRun(id: string): Promise<IngestionRun> { return (await api.get(`/ingestion/runs/${id}`)).data; }
export async function getRuns() { return (await api.get("/ingestion/runs")).data.runs; }
export async function pauseRun(id: string) { return (await api.post(`/ingestion/runs/${id}/pause`)).data; }
export async function resumeRun(id: string) { return (await api.post(`/ingestion/runs/${id}/resume`)).data; }
export async function retryFailed(id: string) { return (await api.post(`/ingestion/runs/${id}/retry-failed`)).data; }
export async function getHealth() { return (await api.get("/health")).data; }
export async function validateCardinality(runId?: string) { return (await api.post("/graph/validate/cardinality", null, {params: {run_id: runId}})).data; }
export async function validateQueries() { return (await api.post("/graph/validate/queries")).data; }
