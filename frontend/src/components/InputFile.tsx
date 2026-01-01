import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import * as React from "react"

interface InputFileProps extends React.InputHTMLAttributes<HTMLInputElement> {
    label?: string
    fileCount?: number
}

export function InputFile({ label = "Upload Images", fileCount, ...props }: InputFileProps) {
    const displayLabel = fileCount !== undefined && fileCount > 0
        ? `${label} (${fileCount})`
        : label

    return (
        <div className="grid w-full max-w-sm items-center gap-3">
            <Label htmlFor="picture">{displayLabel}</Label>
            <Input id="picture" type="file" {...props} />
        </div>
    )
}
