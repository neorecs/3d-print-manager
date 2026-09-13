import type { BambuPrinter } from "./types";

const PRINTING_STATES = new Set(["RUNNING", "PRINTING", "PRINT", "BEZIG"]);
const FINISHED_STATES = new Set(["FINISH", "FINISHED", "FAILED", "STOPPED", "IDLE"]);

export function operationalState(printer: BambuPrinter) {
  if (!printer.active) return "inactief";
  return printer.printer_state?.trim() || "onbekend";
}

export function isPrinting(printer: BambuPrinter) {
  return PRINTING_STATES.has(operationalState(printer).toUpperCase());
}

export function hasStatusMeasurement(printer: BambuPrinter) {
  return Boolean(printer.last_seen_at && printer.printer_state?.trim());
}

export function progressValue(printer: BambuPrinter) {
  if (printer.print_progress === null || printer.print_progress === undefined) return null;
  const value = Number(printer.print_progress);
  return Number.isFinite(value) ? Math.max(0, Math.min(value, 100)) : null;
}

export function progressLabel(printer: BambuPrinter) {
  const progress = progressValue(printer);
  return progress === null ? "Voortgang onbekend" : `${Math.round(progress)}%`;
}

export function remainingTimeLabel(printer: BambuPrinter) {
  const state = operationalState(printer).toUpperCase();
  if (isPrinting(printer)) return "Resterende tijd onbekend";
  if (FINISHED_STATES.has(state)) return "Geen actieve print";
  return "Geen actuele tijdmeting";
}

export function taskLabel(printer: BambuPrinter) {
  if (isPrinting(printer)) return printer.current_task ? `Huidige opdracht: ${printer.current_task}` : "Huidige opdracht onbekend";
  return printer.current_task ? `Laatste bekende opdracht: ${printer.current_task}` : "Geen actieve opdracht bekend";
}

export function temperatureLabel(value?: number | null) {
  if (value === null || value === undefined || !Number.isFinite(Number(value))) return "Onbekend";
  return `${Math.round(Number(value))}°C`;
}

export function lastMeasuredLabel(value?: string | null) {
  if (!value) return "Nog geen printermeting";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "Meetmoment onbekend";
  return `Laatst gemeten: ${date.toLocaleString("nl-NL")}`;
}

export function reachabilityLabel(value?: string | null) {
  const status = (value || "").toLowerCase();
  if (status === "bereikbaar") return "Bereikbaar bij laatste controle";
  if (status.includes("niet_bereikbaar") || status.includes("offline")) return "Niet bereikbaar bij laatste controle";
  return "Niet afzonderlijk gecontroleerd";
}
