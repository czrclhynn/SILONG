import type { Metadata } from 'next';
import './globals.css';
import './theme.css';
export const metadata: Metadata = { title:'SILONG - Urban Heat Intelligence', description:'Explore urban heat exposure across Metro Manila with real ERA5-Land historical reanalysis, PSA census data, and transparent analytics.', icons:{icon:{url:'/silong_logo.png',type:'image/png'}} };
export default function Layout({children}:{children:React.ReactNode}) { return <html lang="en"><body>{children}</body></html> }


