import { forwardRef } from 'react'
import { Button as AntButton, type ButtonProps as AntButtonProps } from 'antd'
import { cn } from './utils/cn'

export type ButtonVariant =
    | 'primary'
    | 'secondary'
    | 'outline'
    | 'default'
    | 'ghost'
    | 'danger'
    | 'text'
    | 'gradient'
    | 'edit'        
    | 'dangerText'  
    

export interface ButtonProps extends Omit<AntButtonProps, 'type' | 'variant'> {
    variant?: ButtonVariant | string
}

const variantConfig: Record<
    ButtonVariant,
    { type?: AntButtonProps['type']; danger?: boolean; className: string }
> = {
    primary: {
        type: 'primary',
        className:
            '!bg-brand-primary hover:!bg-stripe-primary-deep !border-none !h-10 !rounded-lg font-semibold',
    },
    secondary: {
        type: 'default',
        className:
            '!rounded-lg !h-10 !border-stripe-hairline !text-brand-dark hover:!border-brand-primary hover:!text-brand-primary',
    },
    outline: {
        type: 'default',
        className:
            '!rounded-lg !h-10 !border-slate-300 !text-slate-700 hover:!border-brand-primary hover:!text-brand-primary',
    },
    default: {
        type: 'default',
        className:
            '!rounded-lg !h-10 !border-stripe-hairline !text-brand-dark hover:!border-brand-primary hover:!text-brand-primary',
    },
    ghost: {
        type: 'default',
        className:
            '!rounded-lg !border-none !shadow-none !text-slate-500 hover:!text-brand-primary hover:!bg-brand-primary/10',
    },
    danger: {
        type: 'primary',
        danger: true,
        className: '!rounded-lg !h-10 !border-none font-semibold',
    },
    text: {
        type: 'text',
        className: '!rounded-lg hover:!bg-brand-primary/10 !text-brand-primary',
    },
    gradient: {
        type: 'primary',
        className:
            '!h-[45px] !w-full !rounded-lg !border-none !bg-linear-to-br !from-brand-dark !to-brand-primary !text-base !font-bold !text-white hover:!brightness-110 active:!scale-[0.99]',
    },
    edit: {
        type: 'text',
        className:
            '!rounded-lg !bg-brand-primary/10 !text-brand-primary hover:!bg-brand-primary/20',
    },
    dangerText: {
        type: 'text',
        danger: true,
        className:
            '!rounded-lg !bg-red-50 !text-red-500 hover:!bg-red-100',
    },
}

export const Button = forwardRef<HTMLButtonElement | HTMLAnchorElement, ButtonProps>(
    ({ variant = 'primary', className, ...props }, ref) => {
        const config = (variant && (variantConfig as Record<string, any>)[variant]) || variantConfig.primary

        return (
            <AntButton
                ref={ref}
                type={config.type}
                danger={config.danger}
                className={cn(config.className, className)}
                {...props}
            />
        )
    },
)

Button.displayName = 'Button'
