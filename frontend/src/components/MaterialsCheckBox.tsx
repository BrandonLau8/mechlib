import { Checkbox } from "@/components/ui/checkbox"
import {
    Field,
    FieldGroup,
    FieldLabel,
    FieldSet,
} from "@/components/ui/field"
import { Input } from "@/components/ui/input"
import { useState } from "react"

const MATERIAL_OPTIONS = [
    "Plastic",
    "Metal",
    "Rubber",
    "Composite",
    "Ceramic",
    "Wood",
    "Fabric",
]

interface MaterialsCheckBoxProps {
    value: string[]
    onChange: (materials: string[]) => void
    disabled?: boolean
}

export function MaterialsCheckBox({ value, onChange, disabled }: MaterialsCheckBoxProps) {
    const [otherValue, setOtherValue] = useState("")
    const [showOtherInput, setShowOtherInput] = useState(false)

    const handleToggle = (material: string) => {
        if (value.includes(material)) {
            onChange(value.filter(m => m !== material))
        } else {
            onChange([...value, material])
        }
    }

    const handleOtherToggle = () => {
        if (showOtherInput) {
            // Remove any custom materials (not in predefined list)
            const filteredMaterials = value.filter(m => MATERIAL_OPTIONS.includes(m))
            onChange(filteredMaterials)
            setOtherValue("")
        }
        setShowOtherInput(!showOtherInput)
    }

    const handleOtherInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        const customValue = e.target.value
        setOtherValue(customValue)

        if (customValue.trim()) {
            // Remove previous custom material and add new one
            const filteredMaterials = value.filter(m => MATERIAL_OPTIONS.includes(m))
            onChange([...filteredMaterials, customValue.trim()])
        } else {
            // If input is empty, remove custom materials
            const filteredMaterials = value.filter(m => MATERIAL_OPTIONS.includes(m))
            onChange(filteredMaterials)
        }
    }

    return (
        <div className="w-full">
            <FieldSet>
                <FieldLabel>Materials</FieldLabel>
                <FieldGroup className="gap-3">
                    {/* Two column grid for predefined materials */}
                    <div className="grid grid-cols-2 gap-3">
                        {MATERIAL_OPTIONS.map((material) => (
                            <Field orientation="horizontal" key={material}>
                                <Checkbox
                                    id={`material-${material.toLowerCase().replace(/\s+/g, '-')}`}
                                    checked={value.includes(material)}
                                    onCheckedChange={() => handleToggle(material)}
                                    disabled={disabled}
                                />
                                <FieldLabel
                                    htmlFor={`material-${material.toLowerCase().replace(/\s+/g, '-')}`}
                                    className="font-normal"
                                >
                                    {material}
                                </FieldLabel>
                            </Field>
                        ))}
                    </div>

                    {/* Other option */}
                    <Field orientation="horizontal">
                        <Checkbox
                            id="material-other"
                            checked={showOtherInput}
                            onCheckedChange={handleOtherToggle}
                            disabled={disabled}
                        />
                        <FieldLabel htmlFor="material-other" className="font-normal">
                            Other
                        </FieldLabel>
                    </Field>

                    {/* Other input field */}
                    {showOtherInput && (
                        <Field>
                            <Input
                                type="text"
                                placeholder="Enter custom material"
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
