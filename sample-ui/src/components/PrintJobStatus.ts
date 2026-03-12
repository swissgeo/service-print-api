export interface PrintJobStatus {
  created: string;
  finished: string;
  message: string;
  pdfUrl: string;
  reportUrl: string;
  started: string;
  status: "open" | "started" | "processing" | "finished" | "error";
}
