// components/tables/DataTable.jsx
import React from "react";

export default function DataTable({
  title,
  columns = [],
  data = [],
  page = 1,
  maxPage = 1,
  totalItems = 0,
  isLoading = false,
  onPageChange = (newPage) => console.log(`[Stub] Change page to ${newPage}`),
}) {
  return (
    <div className="relative my-8 w-full rounded-xl border border-gray-800 bg-gray-900/90 p-5 shadow-lg backdrop-blur">
      {/* Loading Overlay when changing pages */}
      {isLoading && (
        <div className="absolute inset-0 z-10 flex items-center justify-center rounded-xl bg-gray-950/60 backdrop-blur-sm">
          <span className="text-sm font-semibold text-blue-400">Loading page {page}...</span>
        </div>
      )}

      {/* Header Bar */}
      <div className="mb-4 flex flex-col justify-between gap-2 sm:flex-row sm:items-center">
        <h3 className="text-lg font-bold tracking-wide text-white">{title}</h3>
        <span className="text-xs font-medium text-gray-400">
          Total Items: <span className="text-blue-400">{totalItems}</span>
        </span>
      </div>

      {/* Table Content */}
      <div className="overflow-x-auto rounded-lg border border-gray-800">
        <table className="w-full text-left text-sm text-gray-300">
          <thead className="bg-gray-950/80 text-xs uppercase text-gray-400">
            <tr>
              {columns.map((col) => (
                <th key={col.key} className="px-4 py-3 font-semibold tracking-wider">
                  {col.label}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-800 bg-gray-900/50">
            {data && data.length > 0 ? (
              data.map((row, idx) => (
                <tr key={row.weather_id || row.hotspot_id || idx} className="hover:bg-gray-800/40">
                  {columns.map((col) => (
                    <td key={col.key} className="whitespace-nowrap px-4 py-3">
                      {col.render ? col.render(row[col.key], row) : (row[col.key] ?? "N/A")}
                    </td>
                  ))}
                </tr>
              ))
            ) : (
              <tr>
                <td colSpan={columns.length} className="px-4 py-8 text-center text-gray-500">
                  No records available.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {/* Pagination Bar */}
      <div className="mt-4 flex items-center justify-between border-t border-gray-800 pt-4 text-xs">
        <span className="text-gray-400">
          Page <span className="font-semibold text-white">{page}</span> of{" "}
          <span className="font-semibold text-white">{maxPage}</span>
        </span>

        <div className="flex items-center gap-2">
          <button
            disabled={page <= 1 || isLoading}
            onClick={() => onPageChange(page - 1)}
            className="rounded-md border border-gray-700 bg-gray-950 px-3 py-1.5 font-medium text-gray-300 shadow transition-all hover:bg-gray-800 disabled:cursor-not-allowed disabled:opacity-40"
          >
            Previous
          </button>

          <button
            disabled={page >= maxPage || isLoading}
            onClick={() => onPageChange(page + 1)}
            className="rounded-md border border-gray-700 bg-gray-950 px-3 py-1.5 font-medium text-gray-300 shadow transition-all hover:bg-gray-800 disabled:cursor-not-allowed disabled:opacity-40"
          >
            Next
          </button>
        </div>
      </div>
    </div>
  );
}