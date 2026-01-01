
import { useState, useEffect } from "react"
import { Button } from "@/components/ui/button"
import {Card, CardContent, CardDescription, CardHeader, CardTitle} from "@/components/ui/card.tsx";
import {Dropzone, DropzoneContent, DropzoneEmptyState} from "@/components/ui/shadcn-io/dropzone";

interface ImageUploaderProps {
    files: File[]
    setFiles: (files: File[]) => void
}

export function ImageUploader({ files, setFiles }: ImageUploaderProps) {
    const [previewUrls, setPreviewUrls] = useState<string[]>([])

    // Sync preview URLs with files prop
    useEffect(() => {
        // If files were cleared, clear preview URLs
        if (files.length === 0 && previewUrls.length > 0) {
            previewUrls.forEach(url => {
                if (url) URL.revokeObjectURL(url)
            })
            setPreviewUrls([])
        }
        // If files exist but we don't have preview URLs, create them
        else if (files.length > 0 && previewUrls.length === 0) {
            const newPreviewUrls = files.map(file => {
                if (file.type.startsWith('image/')) {
                    return URL.createObjectURL(file)
                }
                return ''
            })
            setPreviewUrls(newPreviewUrls)
        }
    }, [files, previewUrls])

    const handleDrop = (newFiles: File[]) => {
        console.log('New files dropped:', newFiles);

        // Create preview URLs for the new files only
        const newPreviewUrls = newFiles.map(file => {
            if (file.type.startsWith('image/')) {
                return URL.createObjectURL(file)
            }
            return ''
        })

        // Append new files to existing files
        setFiles([...files, ...newFiles]);
        // Append new preview URLs to existing preview URLs
        setPreviewUrls([...previewUrls, ...newPreviewUrls]);
    };

    const removeFile = (indexToRemove: number) => {
        // Revoke the URL for the removed file
        if (previewUrls[indexToRemove]) {
            URL.revokeObjectURL(previewUrls[indexToRemove])
        }

        setFiles(files.filter((_, index) => index !== indexToRemove))
        setPreviewUrls(previewUrls.filter((_, index) => index !== indexToRemove))
    }

    // Cleanup: revoke all URLs on unmount to prevent memory leaks
    useEffect(() => {
        return () => {
            previewUrls.forEach(url => {
                if (url) URL.revokeObjectURL(url)
            })
        }
    }, [previewUrls])

    return (
        <div className="space-y-4">
                    <Card className="">
                        <CardHeader className="">
                            <CardTitle className="">Mechlib</CardTitle>
                            <CardDescription className="">File upload</CardDescription>
                        </CardHeader>

                        <CardContent className="">
                            <div className="">
                                <Dropzone
                                    maxSize={1024 * 1024 * 10}
                                    minSize={1024}
                                    maxFiles={0}
                                    onDrop={handleDrop}
                                    onError={console.error}
                                    src={files}
                                    className=""
                                >
                                    <DropzoneEmptyState />
                                    <DropzoneContent />
                                </Dropzone>
                            </div>
                        </CardContent>

                        <CardContent>
                            {files.length > 0 && (
                                <div className="space-y-2">
                                    <p className="text-sm font-medium">Selected files ({files.length}):</p>
                                    <div className="space-y-2">
                                        {files.map((file, index) => (
                                            <div key={index} className="flex items-center gap-3 p-3 border rounded-md bg-background shadow-sm">
                                                {file.type.startsWith('image/') && previewUrls[index] && (
                                                    <img
                                                        src={previewUrls[index]}
                                                        alt={file.name}
                                                        className="w-16 h-16 object-cover rounded"
                                                    />
                                                )}
                                                <div className="flex-1 min-w-0">
                                                    <p className="text-sm truncate font-medium">{file.name}</p>
                                                    <p className="text-xs text-muted-foreground">
                                                        {(file.size / 1024).toFixed(1)} KB
                                                    </p>
                                                </div>
                                                <Button
                                                    variant="ghost"
                                                    size="sm"
                                                    onClick={() => removeFile(index)}
                                                >
                                                    Remove
                                                </Button>
                                            </div>
                                        ))}
                                    </div>
                                </div>
                            )}
                        </CardContent>

                    </Card>

        </div>
    )
}

