export type PyodideFS = any;

type FileInfo = {
    name: string;
    content: string;
    type: "text" | "binary";
};

type GetAllFilesOptions = {
    baseDirs?: string[];
    maxDepth?: number;
    getCwd?: () => string | null;
};

type ScanForNewFilesOptions = {
    maxFileSizeBytes?: number;
    maxTotalSizeBytes?: number;
    maxFileCount?: number;
    textExtensions?: string[];
};

// Constants
const DEFAULT_BASE_DIRS = ["/", "/home/pyodide"];
const DEFAULT_MAX_DEPTH = 3;
const DEFAULT_MAX_FILE_SIZE = 10 * 1024 * 1024; // 10MB
const DEFAULT_MAX_TOTAL_SIZE = 50 * 1024 * 1024; // 50MB
const DEFAULT_MAX_FILE_COUNT = 20;
const DEFAULT_TEXT_EXTENSIONS = [
    "txt", "csv", "json", "xml", "html", "md",
    "py", "js", "ts", "css", "yaml", "yml"
];
const EXCLUDED_DIRS = ["dev", "proc", "sys", "tmp"];
const EXCLUDED_PATHS = ["/dev/", "/proc/", "/sys/"];

export function getAllFiles(
    fs: PyodideFS,
    options: GetAllFilesOptions = {}
): Set<string> {
    const {
        baseDirs = DEFAULT_BASE_DIRS,
        maxDepth = DEFAULT_MAX_DEPTH,
        getCwd,
    } = options;

    const allFiles = new Set<string>();
    if (!fs) return allFiles;

    const dirs = [...baseDirs];
    const cwd = getCwd?.();
    if (cwd) dirs.push(cwd);

    function shouldExcludeFile(item: string, fullPath: string): boolean {
        return item.startsWith(".") ||
            item.includes("pyodide") ||
            item.includes("python") ||
            EXCLUDED_PATHS.some(path => fullPath.includes(path));
    }

    function shouldExcludeDir(item: string): boolean {
        return item.startsWith(".") || EXCLUDED_DIRS.includes(item);
    }

    function scanDirectory(path: string, depth: number = 0): void {
        if (depth > maxDepth) return;

        try {
            const items = fs.readdir(path);
            for (const item of items) {
                if (item === "." || item === "..") continue;

                const fullPath = path === "/" ? `/${item}` : `${path}/${item}`;

                try {
                    const stat = fs.stat(fullPath);
                    if (fs.isFile(stat.mode) && !shouldExcludeFile(item, fullPath)) {
                        allFiles.add(fullPath);
                    } else if (fs.isDir(stat.mode) && !shouldExcludeDir(item)) {
                        scanDirectory(fullPath, depth + 1);
                    }
                } catch {
                    // Skip files/dirs that can't be accessed
                }
            }
        } catch {
            // Skip directories that can't be read
        }
    }

    for (const baseDir of dirs) {
        try {
            scanDirectory(baseDir);
        } catch {
            // Skip base directories that can't be accessed
        }
    }

    return allFiles;
}

export function scanForNewFiles(
    fs: PyodideFS,
    existingFiles: Set<string>,
    options: ScanForNewFilesOptions = {}
): FileInfo[] {
    const {
        maxFileSizeBytes = DEFAULT_MAX_FILE_SIZE,
        maxTotalSizeBytes = DEFAULT_MAX_TOTAL_SIZE,
        maxFileCount = DEFAULT_MAX_FILE_COUNT,
        textExtensions = DEFAULT_TEXT_EXTENSIONS,
    } = options;

    const results: FileInfo[] = [];
    if (!fs) return results;

    const currentFiles = getAllFiles(fs, { getCwd: () => safeGetCwd(fs) });
    const newFiles = [...currentFiles].filter(file => !existingFiles.has(file));

    let totalSize = 0;
    let processedCount = 0;

    for (const filePath of newFiles) {
        if (processedCount >= maxFileCount) {
            console.warn(`File count limit reached (${maxFileCount}). Skipping remaining files.`);
            break;
        }

        try {
            const data = fs.readFile(filePath);
            const fileName = filePath.split("/").pop() || "";

            if (data.length > maxFileSizeBytes) {
                console.warn(
                    `File ${fileName} too large (${formatMB(data.length)}MB), skipping. Max size: ${formatMB(maxFileSizeBytes)}MB`
                );
                continue;
            }

            if (totalSize + data.length > maxTotalSizeBytes) {
                console.warn(
                    `Total file size limit reached (${formatMB(maxTotalSizeBytes)}MB). Skipping remaining files.`
                );
                break;
            }

            const { content, type } = processFileData(data, fileName, textExtensions);
            if (content === null) continue; // Skip files that couldn't be processed

            results.push({ name: fileName, content, type });
            totalSize += data.length;
            processedCount++;
        } catch (readError) {
            console.log(`Could not read new file ${filePath}:`, readError);
        }
    }

    if (results.length > 0) {
        console.log(`Processed ${results.length} files, total size: ${formatMB(totalSize)}MB`);
    }

    return results;
}

// Helper functions
function formatMB(bytes: number): string {
    return (bytes / 1024 / 1024).toFixed(1);
}

function processFileData(
    data: Uint8Array,
    fileName: string,
    textExtensions: string[]
): { content: string | null; type: "text" | "binary" } {
    const extension = (fileName.split(".").pop() || "").toLowerCase();

    if (textExtensions.includes(extension)) {
        return {
            content: new TextDecoder().decode(data),
            type: "text"
        };
    }

    try {
        // @ts-ignore btoa is available in worker context
        return {
            content: btoa(String.fromCharCode.apply(null, Array.from(data))),
            type: "binary"
        };
    } catch (error) {
        console.warn(`Failed to encode binary file ${fileName}, skipping:`, error);
        return { content: null, type: "binary" };
    }
}

function safeGetCwd(fs: PyodideFS): string | null {
    try {
        return fs.cwd();
    } catch {
        return null;
    }
}