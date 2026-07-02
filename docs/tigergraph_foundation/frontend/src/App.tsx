import {useMemo, useState} from "react";
import {useMutation, useQuery} from "@tanstack/react-query";
import {
  Alert, AppBar, Box, Button, Card, CardContent, Checkbox, Chip, CircularProgress,
  Container, Divider, FormControlLabel, LinearProgress, Paper, Stack, Tab, Tabs,
  TextField, Toolbar, Tooltip, Typography
} from "@mui/material";
import CloudUploadIcon from "@mui/icons-material/CloudUpload";
import FactCheckIcon from "@mui/icons-material/FactCheck";
import RefreshIcon from "@mui/icons-material/Refresh";
import StorageIcon from "@mui/icons-material/Storage";
import AccountTreeIcon from "@mui/icons-material/AccountTree";
import QueryStatsIcon from "@mui/icons-material/QueryStats";
import ReplayIcon from "@mui/icons-material/Replay";
import {DataGrid, GridColDef} from "@mui/x-data-grid";
import {
  getFiles, getHealth, getQueries, getRun, getRuns, getSchema, pauseRun, resumeRun,
  retryFailed, startRun, validateCardinality, validateFiles, validateQueries
} from "./api";
import type {CatalogFile, IngestionRun, QueryCatalogEntry} from "./types";

const terminal = new Set(["COMPLETED", "COMPLETED_WITH_ERRORS", "FAILED", "CANCELLED"]);
const statusColor = (status: string): "success" | "error" | "primary" | "default" | "warning" => {
  if (status === "COMPLETED" || status === "PASS") return "success";
  if (status === "FAILED" || status === "FAIL" || status === "COMPLETED_WITH_ERRORS") return "error";
  if (status === "RUNNING") return "primary";
  if (status === "SKIPPED") return "default";
  return "warning";
};

function MetricCard({label, value, icon}: {label: string; value: string | number; icon?: React.ReactNode}) {
  return <Card sx={{flex: 1, minWidth: 180}}><CardContent>
    <Stack direction="row" justifyContent="space-between" alignItems="flex-start">
      <Box><Typography color="text.secondary" variant="body2">{label}</Typography><Typography variant="h4" sx={{mt: .5}}>{value}</Typography></Box>
      <Box color="secondary.main">{icon}</Box>
    </Stack>
  </CardContent></Card>;
}

export default function App() {
  const [tab, setTab] = useState(0);
  const [selected, setSelected] = useState<string[]>([]);
  const [runId, setRunId] = useState<string | null>(null);
  const [skipUnchanged, setSkipUnchanged] = useState(true);
  const [batchSize, setBatchSize] = useState(500);
  const [validation, setValidation] = useState<any>(null);
  const [graphValidation, setGraphValidation] = useState<any>(null);
  const [queryValidation, setQueryValidation] = useState<any>(null);
  const [actionError, setActionError] = useState<string | null>(null);

  const files = useQuery({queryKey: ["files"], queryFn: getFiles});
  const health = useQuery({queryKey: ["health"], queryFn: getHealth, refetchInterval: 10000});
  const schema = useQuery({queryKey: ["schema"], queryFn: getSchema});
  const queries = useQuery<QueryCatalogEntry[]>({queryKey: ["queries"], queryFn: getQueries});
  const runs = useQuery({queryKey: ["runs"], queryFn: getRuns, refetchInterval: 5000});
  const run = useQuery<IngestionRun>({
    queryKey: ["run", runId], queryFn: () => getRun(runId!), enabled: !!runId,
    refetchInterval: query => terminal.has(query.state.data?.status ?? "") ? false : 1000
  });

  const validate = useMutation({
    mutationFn: () => validateFiles(selected),
    onSuccess: data => {setValidation(data); setActionError(null);},
    onError: error => setActionError(String(error))
  });
  const start = useMutation({
    mutationFn: () => startRun(selected, skipUnchanged, batchSize),
    onSuccess: data => {setRunId(data.run_id); setTab(1); setActionError(null);},
    onError: error => setActionError(String(error))
  });
  const cardinality = useMutation({
    mutationFn: () => validateCardinality(runId ?? undefined),
    onSuccess: data => {setGraphValidation(data); setActionError(null);},
    onError: error => setActionError(String(error))
  });
  const querySmoke = useMutation({
    mutationFn: validateQueries,
    onSuccess: data => {setQueryValidation(data); setActionError(null);},
    onError: error => setActionError(String(error))
  });

  const rows = (files.data ?? []).map(file => ({...file, id: file.file}));
  const totals = useMemo(() => ({
    files: rows.length,
    vertices: rows.filter(row => row.kind === "vertex").length,
    edges: rows.filter(row => row.kind === "edge").length,
    sourceRows: rows.reduce((sum, row) => sum + row.actual_rows, 0),
    queries: queries.data?.length ?? 0,
    reverseEdges: schema.data?.edges?.filter((edge: any) => edge.reverse_edge).length ?? 0
  }), [rows, queries.data, schema.data]);

  const fileColumns: GridColDef<CatalogFile>[] = [
    {field: "order", headerName: "#", width: 65},
    {field: "kind", headerName: "Kind", width: 100, renderCell: p => <Chip size="small" label={p.value} variant="outlined"/>},
    {field: "target", headerName: "TigerGraph target", minWidth: 260, flex: 1},
    {field: "file", headerName: "CSV file", minWidth: 330, flex: 1.2},
    {field: "actual_rows", headerName: "Rows", type: "number", width: 105},
    {field: "valid", headerName: "Preflight", width: 120, renderCell: p => <Chip size="small" color={p.value ? "success" : "error"} label={p.value ? "Ready" : "Invalid"}/>}
  ];

  const currentRun = run.data;
  const live = health.data?.tigergraph?.mode === "live";
  const healthy = health.data?.tigergraph?.healthy;

  return <Box minHeight="100vh">
    <AppBar position="static" elevation={0} sx={{background: "linear-gradient(110deg,#102A43 0%,#17365D 60%,#006D77 100%)"}}>
      <Toolbar sx={{minHeight: 72}}>
        <Stack direction="row" alignItems="center" spacing={1.5} flex={1}><StorageIcon/><Box>
          <Typography variant="h6">iPerform Insights & Coaching</Typography>
          <Typography variant="caption" sx={{opacity: .82}}>TigerGraph Foundation · Schema, Data Loading and Validation</Typography>
        </Box></Stack>
        <Tooltip title={health.data?.tigergraph?.error ?? health.data?.tigergraph?.restpp_url ?? ""}>
          <Chip label={`${live ? "Live" : "Mock"} TigerGraph · ${healthy ? "Connected" : "Unavailable"}`} color={healthy ? "success" : "error"}/>
        </Tooltip>
      </Toolbar>
    </AppBar>

    <Container maxWidth="xl" sx={{py: 3}}><Stack spacing={2.5}>
      <Box><Typography variant="h4">TigerGraph Data Management</Typography>
        <Typography color="text.secondary">Load the same deterministic graph dataset consumed by all business and agentic-AI pages. React calls FastAPI; FastAPI validates and upserts through RESTPP; SQLite records progress and errors.</Typography>
      </Box>

      {actionError && <Alert severity="error" onClose={() => setActionError(null)}>{actionError}</Alert>}
      {!live && <Alert severity="warning">Mock mode validates orchestration only. Switch <strong>MOCK_TIGERGRAPH=false</strong> and configure RESTPP before claiming live TigerGraph validation.</Alert>}

      <Stack direction={{xs: "column", sm: "row"}} spacing={1.5} flexWrap="wrap">
        <MetricCard label="Schema vertices" value={schema.data?.vertices?.length ?? "—"} icon={<AccountTreeIcon/>}/>
        <MetricCard label="Directed edges" value={schema.data?.edges?.length ?? "—"} icon={<AccountTreeIcon/>}/>
        <MetricCard label="Reverse edges" value={totals.reverseEdges} icon={<AccountTreeIcon/>}/>
        <MetricCard label="CSV files" value={totals.files} icon={<StorageIcon/>}/>
        <MetricCard label="Source rows" value={totals.sourceRows.toLocaleString()} icon={<StorageIcon/>}/>
        <MetricCard label="GSQL queries" value={totals.queries} icon={<QueryStatsIcon/>}/>
      </Stack>

      <Paper><Tabs value={tab} onChange={(_, value) => setTab(value)} variant="scrollable" scrollButtons="auto">
        <Tab label="1. Preflight & Load"/><Tab label="2. Run Progress"/><Tab label="3. Graph Validation"/><Tab label="4. Query Catalog"/><Tab label="5. Run History"/>
      </Tabs><Divider/>

        {tab === 0 && <Box p={2.5}><Stack spacing={2}>
          <Stack direction={{xs: "column", lg: "row"}} spacing={1.5} alignItems={{lg: "center"}}>
            <Button startIcon={<FactCheckIcon/>} variant="outlined" onClick={() => validate.mutate()} disabled={validate.isPending}>Validate {selected.length ? `${selected.length} selected + dependencies` : "all files"}</Button>
            <Button startIcon={<CloudUploadIcon/>} variant="contained" onClick={() => start.mutate()} disabled={start.isPending || !!(currentRun && ["QUEUED","RUNNING"].includes(currentRun.status))}>Load {selected.length ? "selected + dependencies" : "all in dependency order"}</Button>
            <Button startIcon={<RefreshIcon/>} onClick={() => files.refetch()}>Refresh</Button>
            <FormControlLabel control={<Checkbox checked={skipUnchanged} onChange={event => setSkipUnchanged(event.target.checked)}/>} label="Skip unchanged successful files"/>
            <TextField size="small" type="number" label="Batch size" value={batchSize} onChange={event => setBatchSize(Math.max(1, Math.min(10000, Number(event.target.value))))} inputProps={{min: 1, max: 10000}} sx={{width: 140}}/>
          </Stack>
          {validation && <Alert severity={validation.valid ? "success" : "error"}>{validation.valid ? `${validation.files.length} files passed schema, header and dependency preflight.` : "Validation found blocking errors. Review file rows below."}</Alert>}
          <Box height={610}>{files.isLoading ? <Box display="grid" sx={{placeItems: "center", height: "100%"}}><CircularProgress/></Box> :
            <DataGrid rows={rows} columns={fileColumns} checkboxSelection disableRowSelectionOnClick
              onRowSelectionModelChange={(model: any) => setSelected(Array.from(model.ids ?? model).map(String))}
              initialState={{pagination: {paginationModel: {pageSize: 25}}}} pageSizeOptions={[25,50,100]} density="compact"/>}
          </Box>
        </Stack></Box>}

        {tab === 1 && <Box p={2.5}><Stack spacing={2}>
          {!currentRun && <Alert severity="info">Start a load or select a run from Run History.</Alert>}
          {currentRun && <>
            <Stack direction={{xs: "column", md: "row"}} justifyContent="space-between" gap={2}>
              <Box><Typography variant="h6">Run {currentRun.run_id}</Typography><Typography color="text.secondary">{currentRun.message}</Typography></Box>
              <Stack direction="row" spacing={1} alignItems="center"><Chip label={currentRun.status} color={statusColor(currentRun.status)}/>
                {currentRun.status === "RUNNING" && <Button color="warning" onClick={() => pauseRun(currentRun.run_id).then(() => run.refetch())}>Pause</Button>}
                {currentRun.status === "PAUSED" && <Button color="success" onClick={() => resumeRun(currentRun.run_id).then(() => run.refetch())}>Resume</Button>}
                {currentRun.failed_rows > 0 && <Button startIcon={<ReplayIcon/>} color="error" onClick={() => retryFailed(currentRun.run_id).then(data => setRunId(data.run_id))}>Retry failed rows</Button>}
              </Stack>
            </Stack>
            <Box><LinearProgress variant="determinate" value={Math.min(100, currentRun.progress_pct)} sx={{height: 10, borderRadius: 10}}/>
              <Stack direction="row" justifyContent="space-between" mt={1}><Typography variant="body2">{currentRun.progress_pct}% · {currentRun.completed_files}/{currentRun.total_files} files</Typography><Typography variant="body2">{currentRun.succeeded_rows.toLocaleString()} succeeded · {currentRun.failed_rows.toLocaleString()} failed · {currentRun.skipped_rows.toLocaleString()} skipped</Typography></Stack>
            </Box>
            <Box height={460}><DataGrid rows={(currentRun.files ?? []).map(file => ({...file,id:file.file_path}))} density="compact" columns={[
              {field:"file_path",headerName:"File",minWidth:350,flex:1},{field:"target",headerName:"Target",minWidth:260,flex:.8},
              {field:"status",headerName:"Status",width:170,renderCell:p=><Chip size="small" label={p.value} color={statusColor(p.value)}/>},
              {field:"total_rows",headerName:"Rows",width:90},{field:"succeeded_rows",headerName:"Succeeded",width:110},{field:"failed_rows",headerName:"Failed",width:90},{field:"next_row_number",headerName:"Next row",width:100}
            ]}/></Box>
            {currentRun.errors?.length > 0 && <><Typography variant="h6">Row errors</Typography><Box height={300}><DataGrid rows={currentRun.errors.map(error => ({...error,id:error.error_id}))} density="compact" columns={[
              {field:"file_path",headerName:"File",minWidth:300,flex:1},{field:"row_no",headerName:"Row",width:80},{field:"business_key",headerName:"Business key",width:170},{field:"error_code",headerName:"Code",width:150},{field:"error_message",headerName:"Error",minWidth:420,flex:1.5}
            ]}/></Box></>}
          </>}
        </Stack></Box>}

        {tab === 2 && <Box p={2.5}><Stack spacing={2}>
          <Alert severity="info">Cardinality validation compares live TigerGraph vertex/edge counts with the deterministic manifest. Query validation runs all 43 test cases. In mock mode these prove API orchestration only.</Alert>
          <Stack direction={{xs:"column",sm:"row"}} spacing={1.5}>
            <Button variant="contained" startIcon={<FactCheckIcon/>} onClick={() => cardinality.mutate()} disabled={cardinality.isPending}>Validate graph cardinality</Button>
            <Button variant="outlined" startIcon={<QueryStatsIcon/>} onClick={() => querySmoke.mutate()} disabled={querySmoke.isPending}>Run 43 query smoke tests</Button>
          </Stack>
          {graphValidation && <Alert severity={graphValidation.passed ? "success" : "error"}>Cardinality validation {graphValidation.passed ? "passed" : "failed"} in {graphValidation.mode} mode ({graphValidation.results.length} checks).</Alert>}
          {queryValidation && <Alert severity={queryValidation.passed ? "success" : "error"}>Query smoke suite {queryValidation.passed ? "passed" : "failed"} in {queryValidation.mode} mode ({queryValidation.results.length} cases).</Alert>}
          {graphValidation?.results && <Box height={460}><DataGrid rows={graphValidation.results.map((item:any,index:number)=>({...item,id:index}))} density="compact" columns={[
            {field:"rule_id",headerName:"Rule",minWidth:360,flex:1},{field:"status",headerName:"Status",width:110,renderCell:p=><Chip size="small" label={p.value} color={statusColor(p.value)}/>},{field:"expected",headerName:"Expected",width:110},{field:"actual",headerName:"Actual",width:110},{field:"message",headerName:"Message",minWidth:300,flex:1}
          ]}/></Box>}
        </Stack></Box>}

        {tab === 3 && <Box p={2.5}><Stack spacing={1.5}>
          <Alert severity="warning">Catalog status is intentionally <strong>live-compile-pending</strong> until the supplied install and live-validation scripts run against TigerGraph 4.2.2.</Alert>
          <Box height={620}><DataGrid rows={(queries.data ?? []).map(query => ({...query,id:query.id}))} density="compact" columns={[
            {field:"id",headerName:"ID",width:90},{field:"name",headerName:"Query",minWidth:280,flex:.8},{field:"purpose",headerName:"Purpose",minWidth:420,flex:1.2},{field:"parameters",headerName:"Parameters",minWidth:360,flex:1},{field:"status",headerName:"Validation status",minWidth:260,flex:.7}
          ]} pageSizeOptions={[25,43]} initialState={{pagination:{paginationModel:{pageSize:25}}}}/></Box>
        </Stack></Box>}

        {tab === 4 && <Box p={2.5}><Box height={620}><DataGrid rows={(runs.data ?? []).map((item:any)=>({...item,id:item.run_id}))} density="compact" onRowDoubleClick={params => {setRunId(String(params.row.run_id)); setTab(1);}} columns={[
          {field:"started_at",headerName:"Started",minWidth:210,flex:.7},{field:"run_id",headerName:"Run ID",minWidth:300,flex:1},{field:"mode",headerName:"Mode",width:160},{field:"status",headerName:"Status",width:170,renderCell:p=><Chip size="small" label={p.value} color={statusColor(p.value)}/>},{field:"total_files",headerName:"Files",width:90},{field:"succeeded_rows",headerName:"Succeeded",width:120},{field:"failed_rows",headerName:"Failed",width:90},{field:"message",headerName:"Message",minWidth:260,flex:1}
        ]}/></Box></Box>}
      </Paper>
    </Stack></Container>
  </Box>;
}
