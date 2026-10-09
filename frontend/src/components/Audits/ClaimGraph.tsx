import { useQuery } from "@tanstack/react-query"
import { useState } from "react"
import { livingTrustApi } from "@/api/livingTrust"
import { QueryState, StatusPill } from "./shared"

export function ClaimGraph({auditId,completed,onPreview}:{auditId:string;completed:boolean;onPreview:(id:string)=>void}) {
 const [offset,setOffset]=useState(0),[selected,setSelected]=useState("")
 const result=useQuery({queryKey:["claim-graph",auditId,offset],queryFn:()=>livingTrustApi.graph(auditId,offset),enabled:completed})
 if(!completed)return null
 const data=result.data,claims=data?.nodes.filter(n=>n.kind==="claim")||[]
 const claim=claims.find(c=>c.id===selected)||claims[0]
 const edges=data?.edges.filter(e=>e.to===claim?.id&&data?.nodes.some(n=>n.id===e.from&&n.kind==="evidence"))||[]
 const node=(id:string)=>data?.nodes.find(n=>n.id===id)
 return <section className="product-panel claim-graph"><h2>Claim Graph</h2><p>Follow each AI claim to its current source quotes. Candidate evidence has no established support verdict.</p><QueryState loading={result.isPending} error={result.error} retry={()=>result.refetch()}/>{data?.assessment_stale&&<p role="status">The documents changed. Re-audit to refresh the claim assessment; quote comparisons below refer to the current literal text.</p>}
 {data&&!claims.length&&<p>No extracted claims on this page. Run the audit to build the graph.</p>}
 {!!claims.length&&<div className="claim-graph-grid"><nav aria-label="Choose a claim"><h3>AI claims</h3>{claims.map(c=><button type="button" className="graph-claim-button" key={c.id} aria-pressed={c.id===claim?.id} onClick={()=>setSelected(c.id)}>{c.label}<StatusPill status={c.status||"extracted"}/></button>)}</nav><div><h3>Claim → source evidence</h3>{claim&&<article className="source-fact-record"><blockquote>{claim.label}</blockquote>{claim.status==="not_anchored"&&<p role="status">This statement is not present in the current AI document. It cannot provide a source-backed trust rating.</p>}<button type="button" className="secondary-button" onClick={()=>onPreview(claim.document_id)}>Open AI document</button></article>}{!edges.length&&<p>No current, literal source quote is linked to this claim.</p>}{edges.map(edge=>{const evidence=node(edge.from);if(!evidence)return null;const source=data?.nodes.find(n=>n.kind==="document"&&n.document_id===evidence.document_id);return <article className="source-fact-record" key={edge.from}><StatusPill status={edge.relation}/>{evidence.reviewer_selected&&<StatusPill status="Reviewer-selected source"/>}<blockquote>{evidence.label}</blockquote><p>{source?.label} · Source version {source?.version}</p><button type="button" className="secondary-button" onClick={()=>onPreview(evidence.document_id)}>Open source document</button></article>})}</div></div>}
 {data&&<div className="policy-actions"><button type="button" className="secondary-button" disabled={!offset||result.isFetching} onClick={()=>{setOffset(Math.max(0,offset-25));setSelected("")}}>Previous claims</button><span>{claims.length?`${offset+1}–${offset+claims.length}`:"0"} of {data.total_claims} claims</span><button type="button" className="secondary-button" disabled={!data.has_more||result.isFetching} onClick={()=>{setOffset(offset+25);setSelected("")}}>Next claims</button></div>}</section>
}
