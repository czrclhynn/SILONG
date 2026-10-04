'use client';
import * as Dialog from '@radix-ui/react-dialog';
import { X } from 'lucide-react';
export function Sheet({open,onOpenChange,title,children}:{open:boolean;onOpenChange:(v:boolean)=>void;title:string;children:React.ReactNode}){return <Dialog.Root open={open} onOpenChange={onOpenChange}><Dialog.Portal><Dialog.Overlay className="sheet-overlay"/><Dialog.Content className="sheet"><Dialog.Title>{title}</Dialog.Title><Dialog.Description className="muted">Historical reanalysis · calculated indicators</Dialog.Description><Dialog.Close className="icon-button close" aria-label="Close detail panel"><X size={20}/></Dialog.Close>{children}</Dialog.Content></Dialog.Portal></Dialog.Root>}

