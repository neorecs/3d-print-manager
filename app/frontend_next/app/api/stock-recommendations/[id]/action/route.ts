import { NextRequest, NextResponse } from "next/server";

const API_BASE_URL = process.env.API_BASE_URL || process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:38080";

const actionPaths = {
  accept: "accept",
  ignore: "ignore",
  "convert-to-print-job": "convert-to-print-job",
} as const;

export async function POST(request: NextRequest, { params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const payload = await request.json().catch(() => ({}));
  const action = payload.action as keyof typeof actionPaths;

  if (!actionPaths[action]) {
    return NextResponse.json({ detail: "Onbekende voorraadadviesactie" }, { status: 400 });
  }

  const response = await fetch(`${API_BASE_URL}/stock-recommendations/${id}/${actionPaths[action]}`, {
    method: "POST",
  });

  const data = await response.json().catch(() => ({ detail: "Backend gaf geen JSON terug" }));
  return NextResponse.json(data, { status: response.status });
}
