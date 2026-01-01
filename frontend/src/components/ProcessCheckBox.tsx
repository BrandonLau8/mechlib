import { Checkbox } from "@/components/ui/checkbox"
import {
    Field,
    FieldGroup,
    FieldLabel,
    FieldSet,
} from "@/components/ui/field"
import { Input } from "@/components/ui/input"
import { useState } from "react"

const PROCESS_OPTIONS = [
    "Injection Molding",
    "Blow Molding",
    "Compression Molding",
    "Roto Molding",
    "Casting",
    "Bending",
    "Rolling",
    "Stamping",
    "Drawing",
    "Deep Drawing",
    "Extrusion",
    "Die Casting",
    "Welding",
    "CNC",
    "Adhesive",
    "Mechanical Fastening",
    "Assembly",
]

interface ProcessCheckBoxProps {
    value: string[]
    onChange: (process: string[]) => void
    disabled?: boolean
}

export function ProcessCheckBox({ value, onChange, disabled }: ProcessCheckBoxProps) {
    const [otherValue, setOtherValue] = useState("")
    const [showOtherInput, setShowOtherInput] = useState(false)

    const handleToggle = (process: string) => {
        if (value.includes(process)) {
            onChange(value.filter(p => p !== process))
        } else {
            onChange([...value, process])
        }
    }

    const handleOtherToggle = () => {
        if (showOtherInput) {
            // Remove any custom processes (not in predefined list)
            const filteredProcesses = value.filter(p => PROCESS_OPTIONS.includes(p))
            onChange(filteredProcesses)
            setOtherValue("")
        }
        setShowOtherInput(!showOtherInput)
    }

    const handleOtherInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        const customValue = e.target.value
        setOtherValue(customValue)

        if (customValue.trim()) {
            // Remove previous custom process and add new one
            const filteredProcesses = value.filter(p => PROCESS_OPTIONS.includes(p))
            onChange([...filteredProcesses, customValue.trim()])
        } else {
            // If input is empty, remove custom processes
            const filteredProcesses = value.filter(p => PROCESS_OPTIONS.includes(p))
            onChange(filteredProcesses)
        }
    }

    return (
        <div className="w-full">
            <FieldSet>
                <FieldLabel>Process</FieldLabel>
                <FieldGroup className="gap-3">
                    {/* Two column grid for predefined processes */}
                    <div className="grid grid-cols-2 gap-3">
                        {PROCESS_OPTIONS.map((process) => (
                            <Field orientation="horizontal" key={process}>
                                <Checkbox
                                    id={`process-${process.toLowerCase().replace(/\s+/g, '-')}`}
                                    checked={value.includes(process)}
                                    onCheckedChange={() => handleToggle(process)}
                                    disabled={disabled}
                                />
                                <FieldLabel
                                    htmlFor={`process-${process.toLowerCase().replace(/\s+/g, '-')}`}
                                    className="font-normal"
                                >
                                    {process}
                                </FieldLabel>
                            </Field>
                        ))}
                    </div>

                    {/* Other option */}
                    <Field orientation="horizontal">
                        <Checkbox
                            id="process-other"
                            checked={showOtherInput}
                            onCheckedChange={handleOtherToggle}
                            disabled={disabled}
                        />
                        <FieldLabel htmlFor="process-other" className="font-normal">
                            Other
                        </FieldLabel>
                    </Field>

                    {/* Other input field */}
                    {showOtherInput && (
                        <Field>
                            <Input
                                type="text"
                                placeholder="Enter custom process"
                                value={otherValue}
                                onChange={handleOtherInputChange}
                                disabled={disabled}
                                className="mt-2"
                            />
                        </Field>
                    )}
                </FieldGroup>
            </FieldSet>
        </div>
    )
}
