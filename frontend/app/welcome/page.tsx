'use client';
import {useEffect,useState} from 'react';
import dynamic from 'next/dynamic';
import {BrandLogo} from '@/components/layout/brand-logo';
import {MapPin,Database} from 'lucide-react';
import {Bundle,decodeBundle} from '@/lib/types';
import {rowsAt} from '@/lib/analytics';
import {Button} from '@/components/ui/button';
const HeatMap=dynamic(()=>import('@/components/maps/heat-map'),{ssr:false});
export default function Welcome(){const [bundle,setBundle]=useState<Bundle|null>(null);useEffect(()=>{fetch('/data/dataset.json').then(r=>r.json()).then(d=>setBundle(decodeBundle(d))).catch(()=>{})},[]);return <div className="welcome"><header><a href="/" className="brand"><BrandLogo/></a><a href="/#Methodology">Our methodology</a></header><main><div className="welcome-copy"><span className="eyebrow"><MapPin size={14}/> METRO MANILA, PHILIPPINES</span><h1>Understand urban heat.<br/>See who is exposed.<br/><em>Explore what could change.</em></h1><p>SILONG combines environmental, weather, population, and geospatial data to analyze urban heat exposure across Metro Manila.</p><div className="welcome-actions"><Button asChild><a href="/">Explore Dashboard</a></Button><Button asChild variant="outline"><a href="/#Methodology">View Methodology</a></Button></div><div className="welcome-note"><Database size={15}/>Real historical data · 17 areas · transparent methodology</div></div><div className="panel welcome-map">{bundle?<HeatMap rows={rowsAt(bundle,'2025-12-31',14)} config={bundle.config} onSelect={()=>{window.location.href='/#Heat%20Map'}}/>:<div className="skeleton" style={{height:420}}/>}</div></main><footer>SILONG — Urban Heat Risk Intelligence Platform. Analytical estimates, not official government warnings.</footer></div>}


