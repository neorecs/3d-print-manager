export type LoadResult<T> = { data: T; error: null } | { data: null; error: string };

export async function loadResult<T>(request: Promise<T>): Promise<LoadResult<T>> {
  try { return { data: await request, error: null }; }
  catch (error) { return { data: null, error: error instanceof Error ? error.message : "Gegevens konden niet worden geladen" }; }
}
