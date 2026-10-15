"use client";

import { useState, useEffect, useRef } from "react";
import { Search, Loader2, X, Package, Check, ChevronRight } from "lucide-react";
import { api } from "@/lib/api";
import { formatCurrency } from "@/lib/utils";

export interface SearchProduct {
  id: string;
  sku: string;
  name: string;
  brand: string;
  category: string;
  description: string;
  image_url?: string | null;
  unit_price: number;
}

interface SkuAutocompleteProps {
  onSelectProduct: (product: SearchProduct) => void;
  disabled?: boolean;
  placeholder?: string;
}

export function SkuAutocomplete({
  onSelectProduct,
  disabled = false,
  placeholder = "Search SKU or product name (e.g., LG-SET-1, Inverter, Tubular)...",
}: SkuAutocompleteProps) {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<SearchProduct[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isOpen, setIsOpen] = useState(false);
  const [selectedIndex, setSelectedIndex] = useState(-1);
  const [hasSearched, setHasSearched] = useState(false);

  const containerRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  // Debounced search effect
  useEffect(() => {
    if (!query.trim()) {
      setResults([]);
      setIsLoading(false);
      setIsOpen(false);
      setHasSearched(false);
      return;
    }

    const timer = setTimeout(async () => {
      setIsLoading(true);
      try {
        const data = await api.get<SearchProduct[]>(
          `/agent/products/search?q=${encodeURIComponent(query.trim())}&limit=10`
        );
        setResults(data);
        setIsOpen(true);
        setSelectedIndex(-1);
        setHasSearched(true);
      } catch (err) {
        console.error("SKU search error:", err);
        setResults([]);
      } finally {
        setIsLoading(false);
      }
    }, 250);

    return () => clearTimeout(timer);
  }, [query]);

  // Click outside listener
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (!isOpen || results.length === 0) {
      if (e.key === "ArrowDown" && query.trim() && results.length > 0) {
        setIsOpen(true);
      }
      return;
    }

    if (e.key === "ArrowDown") {
      e.preventDefault();
      setSelectedIndex((prev) => (prev < results.length - 1 ? prev + 1 : 0));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setSelectedIndex((prev) => (prev > 0 ? prev - 1 : results.length - 1));
    } else if (e.key === "Enter") {
      e.preventDefault();
      if (selectedIndex >= 0 && selectedIndex < results.length) {
        handleSelect(results[selectedIndex]);
      }
    } else if (e.key === "Escape") {
      e.preventDefault();
      setIsOpen(false);
    }
  };

  const handleSelect = (product: SearchProduct) => {
    onSelectProduct(product);
    setQuery("");
    setResults([]);
    setIsOpen(false);
    setSelectedIndex(-1);
  };

  const handleClear = () => {
    setQuery("");
    setResults([]);
    setIsOpen(false);
    inputRef.current?.focus();
  };

  return (
    <div ref={containerRef} className="relative w-full">
      {/* Search Input Bar */}
      <div className="relative flex items-center">
        <Search className="absolute left-3.5 w-4 h-4 text-slate-400 pointer-events-none" />
        <input
          ref={inputRef}
          type="text"
          value={query}
          disabled={disabled}
          onChange={(e) => setQuery(e.target.value)}
          onFocus={() => {
            if (results.length > 0) setIsOpen(true);
          }}
          onKeyDown={handleKeyDown}
          placeholder={placeholder}
          className="w-full pl-10 pr-10 py-3 bg-slate-50 border-2 border-slate-200 focus:border-red-600 focus:bg-white rounded-xl text-xs font-semibold text-slate-900 placeholder:text-slate-400 transition outline-none shadow-sm"
        />
        <div className="absolute right-3 flex items-center space-x-1.5">
          {isLoading && <Loader2 className="w-4 h-4 text-red-600 animate-spin" />}
          {query && !isLoading && (
            <button
              type="button"
              onClick={handleClear}
              className="p-1 text-slate-400 hover:text-slate-600 rounded-full hover:bg-slate-100 transition"
              title="Clear search"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          )}
        </div>
      </div>

      {/* Suggestion Dropdown Panel */}
      {isOpen && (
        <div className="absolute z-50 left-0 right-0 mt-1.5 bg-white border border-slate-200 rounded-xl shadow-2xl overflow-hidden max-h-80 overflow-y-auto">
          {results.length > 0 ? (
            <div className="divide-y divide-slate-100">
              <div className="px-3 py-1.5 bg-slate-50 text-[10px] font-bold text-slate-500 uppercase tracking-wider flex justify-between">
                <span>Matching Authorized Products ({results.length})</span>
                <span className="text-slate-400">↑↓ to navigate • Enter to select</span>
              </div>
              {results.map((product, idx) => {
                const isSelected = idx === selectedIndex;
                return (
                  <div
                    key={product.id}
                    onMouseEnter={() => setSelectedIndex(idx)}
                    onClick={() => handleSelect(product)}
                    className={`p-3 flex items-center gap-3 cursor-pointer transition ${
                      isSelected ? "bg-red-50/70 border-l-4 border-red-600" : "hover:bg-slate-50"
                    }`}
                  >
                    {/* Thumbnail */}
                    <div className="w-12 h-12 bg-white rounded-lg border border-slate-200 flex items-center justify-center overflow-hidden shrink-0 p-1">
                      {product.image_url ? (
                        <img
                          src={product.image_url}
                          alt={product.name}
                          className="w-full h-full object-contain"
                          onError={(e) => {
                            (e.target as HTMLImageElement).style.display = "none";
                          }}
                        />
                      ) : (
                        <Package className="w-5 h-5 text-slate-400" />
                      )}
                    </div>

                    {/* Product Meta */}
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <span className="font-mono text-[10px] font-extrabold px-1.5 py-0.5 rounded bg-slate-900 text-white">
                          {product.sku}
                        </span>
                        <span className="text-[10px] font-bold uppercase text-red-600 bg-red-50 px-1.5 py-0.5 rounded">
                          {product.category}
                        </span>
                      </div>
                      <div className="font-bold text-xs text-slate-900 truncate mt-0.5">
                        {product.name}
                      </div>
                      {product.description && (
                        <div className="text-[10px] text-slate-500 truncate mt-0.5">
                          {product.description.replace(/\n/g, " ")}
                        </div>
                      )}
                    </div>

                    {/* Unit Price */}
                    <div className="text-right shrink-0">
                      <div className="font-extrabold text-xs text-slate-900">
                        {formatCurrency(product.unit_price)}
                      </div>
                      <div className="text-[9px] text-slate-400 font-semibold">Excl. Tax</div>
                    </div>

                    <ChevronRight className={`w-4 h-4 shrink-0 ${isSelected ? "text-red-600" : "text-slate-300"}`} />
                  </div>
                );
              })}
            </div>
          ) : hasSearched && !isLoading ? (
            <div className="p-6 text-center">
              <Package className="w-8 h-8 text-slate-300 mx-auto mb-2" />
              <div className="text-xs font-bold text-slate-700">No matching products found</div>
              <div className="text-[11px] text-slate-400 mt-1">
                No active Livguard product matches &ldquo;{query}&rdquo;.
              </div>
            </div>
          ) : null}
        </div>
      )}
    </div>
  );
}
