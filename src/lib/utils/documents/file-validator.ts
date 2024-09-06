import {
    SUPPORTED_FILE_EXTENSIONS,
    SUPPORTED_FILE_TYPE,
    MAX_FILE_SIZE_BYTES,
    SUPPORTED_AUDIO_MIME_TYPES,
 } from '$lib/constants';


export function isValidFileType(file: File): boolean {
    const fileType = file['type'];
    const fileExtension = file.name.split('.').at(-1);

    return SUPPORTED_FILE_TYPE.includes(fileType) || SUPPORTED_FILE_EXTENSIONS.includes(String(fileExtension));
}

export function isValidAudioFileSize(file: File): boolean {
    return file.size <= MAX_FILE_SIZE_BYTES;
}

export function isMoreThan25Mb(file: File): boolean {
    return file.size >= MAX_FILE_SIZE_BYTES;
}

export function isAudioFile(file: File): boolean {
    const fileType = file.type;
    return SUPPORTED_AUDIO_MIME_TYPES.includes(fileType);
}

export function validateFiles(files: FileList) {
    const errors: string[] = [];

    let validFiles = Array.from(files).filter(file => {
        if (!isValidFileType(file)) {
            errors.push(`Unsupported file type - ${file.name}: Supported types are: ${SUPPORTED_FILE_EXTENSIONS.join(', ')}.`);
            return false;
        }

        if (isAudioFile(file) && !isValidAudioFileSize(file)) {
            errors.push(`The file ${file.name} exceeds the 25 MB size limit. Please upload a smaller file.`);
            return false;
        }

        return true;
    });

    return { validFiles, errors };
}