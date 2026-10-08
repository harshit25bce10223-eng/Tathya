// Run from the repository root against the frontend production preview on port 4173.
require('node:fs').mkdirSync('artifacts/ui-review',{recursive:true});
const {chromium,expect}=require('@playwright/test');
const id='11111111-1111-4111-8111-111111111111';
const records=[{id,title:'Preview · Cloud procurement agreement',status:'completed',created_at:'2026-10-08T10:00:00Z',updated_at:'2026-10-08T10:05:00Z'},...['Vendor onboarding','Annual services agreement','Delivery schedule','Security policy'].map((title,i)=>({id:`audit-${i}`,title:`Preview · ${title}`,status:['completed','processing','queued','failed'][i],created_at:'2026-10-08T09:00:00Z',updated_at:'2026-10-08T09:05:00Z'}))];
let flags=[{id:'flag-1',audit_id:id,document_id:'document-1',claim_id:null,type:'COMMERCIAL_VALUE',severity:'CRITICAL',materiality:'MATERIAL',reason:'The draft states ₹1.25 crore; the approved schedule lists ₹83.4 lakh. The ₹41.6 lakh difference requires a reviewer decision.',suggested_fix:'Reconcile the contract value against the latest approved commercial schedule.',status:'pending',reviewer_note:null,impact_score:28,location_json:'{"page":3,"section":"4.2"}'},{id:'flag-2',audit_id:id,document_id:'document-2',claim_id:null,type:'DELIVERY_DATE',severity:'HIGH',materiality:'HIGH',reason:'The delivery date differs between the draft and the signed schedule.',suggested_fix:'Confirm the signed delivery milestone with the project owner.',status:'pending',reviewer_note:null,impact_score:14,location_json:'{"page":7,"section":"2.1"}'}];
const documents=[{id:'document-1',filename:'Procurement_Agreement_Draft.pdf',kind:'primary',version_no:1,text_hash:'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855',is_current:true},{id:'document-2',filename:'Approved_Commercial_Schedule.xlsx',kind:'primary',version_no:2,text_hash:'b5af45644298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b8',is_current:true}];
let score=58,role='reviewer',mode='normal',submitted=false,decisions=0,summaryCalls=0;
(async()=>{
 const browser=await chromium.launch({headless:true,channel:'chromium'});
 const page=await browser.newPage({viewport:{width:1440,height:1000}});
 const errors=[];page.on('pageerror',e=>errors.push(e.message));
 await page.addInitScript(()=>{sessionStorage.setItem('tathya-splash-seen','1');localStorage.setItem('access_token','design-preview');localStorage.setItem('vite-ui-theme','light')});
 await page.route('**/api/v1/users/me',r=>r.fulfill({json:{id:'preview',email:'preview@example.in',full_name:'Preview Reviewer',is_active:true,is_superuser:false,role}}));
 await page.route('**/api/v1/audits**',async r=>{
  const path=new URL(r.request().url()).pathname;
  if(mode==='unavailable'){await r.fulfill({status:404,json:{detail:'Not Found'}});return}
  if(path.endsWith('/decision')){const body=r.request().postDataJSON();if(!body.note)throw Error('Missing reviewer note');flags=flags.map(f=>path.includes(f.id)?{...f,status:body.action==='dismiss'?'dismissed':'accepted',reviewer_note:body.note}:f);decisions++;await r.fulfill({json:{id:'decision-1'}});return}
  if(path.endsWith('/rescore')){score=86;await r.fulfill({json:{trust_score:score}});return}
  if(path.endsWith('/flags')){await r.fulfill({json:{data:mode==='processing'&&summaryCalls<2?[]:flags,count:flags.length}});return}
  if(path.endsWith('/documents')){await r.fulfill({json:{data:documents,count:2}});return}
  if(path.endsWith('/audits')&&r.request().method()==='POST'){const body=r.request().postDataBuffer().toString();if(!body.includes('filename="agreement.txt"')||!body.includes('Draft agreement'))throw Error('Multipart file data missing');submitted=true;await r.fulfill({status:201,json:records[0]});return}
  if(path.endsWith('/audits')&&mode==='malformed'){await r.fulfill({json:{data:[{id:'broken'}],count:1}});return} if(path.endsWith('/audits')){await r.fulfill({json:{data:mode==='empty'?[]:records,count:mode==='empty'?0:records.length}});return}
  if(mode==='processing')summaryCalls++; await r.fulfill({json:{audit:{...records[0],status:mode==='processing'&&summaryCalls<2?'processing':'completed'},document_count:2,flag_count:2,open_flag_count:flags.filter(f=>f.status==='pending').length,claim_count:24,passport:{trust_score:score,status:'VERIFIED',verify_token:'previewtoken'}}});
 });
 await page.goto('http://127.0.0.1:4173/submit');
 await expect(page.getByRole('heading',{name:'Start with your documents.'})).toBeVisible();
 await expect(page.getByRole('button',{name:'Start verification'})).toBeDisabled();
 await page.getByLabel('Upload documents').setInputFiles({name:'bad.exe',mimeType:'application/octet-stream',buffer:Buffer.from('bad')});
 await expect(page.getByRole('alert')).toContainText('supported');
 await page.getByLabel('Audit name').fill('Preview · Cloud procurement agreement');
 await page.getByLabel('Upload documents').setInputFiles([{name:'agreement.txt',mimeType:'text/plain',buffer:Buffer.from('Draft agreement')},{name:'schedule.csv',mimeType:'text/csv',buffer:Buffer.from('value,date\n8340000,2026-11-01')}]);
 await page.screenshot({path:'artifacts/ui-review/submit-desktop-v2.png',fullPage:true,timeout:60000});
 await page.getByRole('button',{name:'Remove schedule.csv'}).click();const drop=await page.evaluateHandle(()=>{const transfer=new DataTransfer();transfer.items.add(new File(['Supporting schedule'],'drop.txt',{type:'text/plain'}));return transfer});await page.locator('.file-drop').dispatchEvent('drop',{dataTransfer:drop});await expect(page.getByRole('button',{name:'Remove drop.txt'})).toBeVisible();await page.getByRole('button',{name:'Remove drop.txt'}).click();
 await page.getByRole('button',{name:'Start verification'}).click();
 await expect(page.getByRole('heading',{name:'YOUR AUDIT RESULT',exact:false})).toHaveCount(0);
 await expect(page.getByRole('heading',{name:'Understand the score'})).toBeVisible();
 await expect(page.getByText('Procurement_Agreement_Draft.pdf',{exact:true})).toBeVisible();
 await page.screenshot({path:'artifacts/ui-review/result-desktop-v2.png',fullPage:true,timeout:60000});
 await page.goto('http://127.0.0.1:4173/control');
 await expect(page.getByRole('heading',{name:'Control center',exact:true})).toBeVisible();
 await expect(page.getByRole('link',{name:'Preview · Cloud procurement agreement',exact:true})).toBeVisible();
 await page.screenshot({path:'artifacts/ui-review/control-desktop-v2.png',fullPage:true,timeout:60000});
 await page.getByLabel('Search audits').fill('Security');await expect(page.locator('tbody tr')).toHaveCount(1);
 await page.getByLabel('Search audits').fill('');await page.getByLabel('Filter by status').selectOption('active');await expect(page.locator('tbody tr')).toHaveCount(2);
 await page.goto('http://127.0.0.1:4173/control/queue');await expect(page.getByRole('heading',{name:'Review queue',exact:true})).toBeVisible();
 await page.getByRole('link',{name:'Preview · Cloud procurement agreement',exact:true}).click();
 await expect(page.getByRole('heading',{name:'COMMERCIAL VALUE'})).toBeVisible();
 await expect(page.getByRole('button',{name:'Dismiss',exact:true})).toBeDisabled();
 await page.screenshot({path:'artifacts/ui-review/investigation-desktop-v2.png',fullPage:true,timeout:60000});
 await page.locator('summary').click();await expect(page.locator('pre')).toContainText('document_version_id');
 await page.getByLabel('Reviewer note').fill('Checked the approved schedule. The draft amount is incorrect.');
 await page.getByRole('button',{name:'Dismiss',exact:true}).click();await expect(page.getByRole('status')).toContainText('Decision saved');
 await page.getByRole('button',{name:'Recalculate score'}).click();await expect(page.getByRole('status')).toContainText('Score recalculated');
 for(const [path,name,heading] of [['/submit','submit-mobile-v2','Start with your documents.'],['/submit/'+id,'result-mobile-v2','Understand the score'],['/control','control-mobile-v2','Control center']]){await page.setViewportSize({width:390,height:844});await page.goto('http://127.0.0.1:4173'+path);await expect(page.getByRole('heading',{name:heading,exact:true})).toBeVisible();await page.waitForTimeout(150);await page.screenshot({path:'artifacts/ui-review/'+name+'.png',fullPage:true,timeout:60000});if(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth))throw Error('Horizontal overflow '+path)}
 role='submitter';await page.goto('http://127.0.0.1:4173/control/queue');await expect(page.getByRole('heading',{name:'Reviewer access required'})).toBeVisible();
 mode='empty';await page.goto('http://127.0.0.1:4173/control');await expect(page.getByRole('heading',{name:'Your first audit starts here'})).toBeVisible();
 mode='unavailable';await page.reload();await expect(page.getByRole('heading',{name:'Audit service is unavailable'})).toBeVisible({timeout:15000});await page.screenshot({path:'artifacts/ui-review/service-unavailable-v2.png',fullPage:true,timeout:60000});
 mode='malformed';await page.reload();await expect(page.getByText('The audit service returned incomplete data. Please refresh or try again later.',{exact:true})).toBeVisible({timeout:15000});mode='processing';await page.goto('http://127.0.0.1:4173/submit/'+id);await expect(page.getByText('Verification is processing. This page updates automatically.',{exact:true})).toBeVisible();await expect(page.getByRole('heading',{name:'COMMERCIAL VALUE',exact:true})).toBeVisible({timeout:15000});if(!submitted||decisions!==1||errors.length)throw Error(JSON.stringify({submitted,decisions,errors}));
 console.log(JSON.stringify({passed:true,submitted,decisions,errors,checks:['file validation','drag and drop','multipart upload','result navigation','search','status filter','decision note requirement','decision save','rescore','mobile overflow','reviewer access','empty state','API unavailable','malformed response','completion refresh']}));
 await browser.close();
})().catch(e=>{console.error(e);process.exit(1)});


