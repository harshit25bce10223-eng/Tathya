const { chromium } = require('@playwright/test');
(async () => {
 const browser = await chromium.launch({headless:true,channel:'chromium'});
 const page = await browser.newPage({viewport:{width:1440,height:1000},deviceScaleFactor:1});
 const errors=[]; page.on('pageerror', e=>errors.push(e.message));
 await page.goto('http://127.0.0.1:4173/login');
 await page.getByRole('heading',{name:'Welcome back.'}).waitFor();
 await page.screenshot({path:'artifacts/ui-review/login-desktop.png',fullPage:true});
 await page.getByRole('button',{name:'Sign in to Tathya'}).click();
 await page.getByText('Invalid email address',{exact:true}).waitFor();
 await page.getByText('Password is required',{exact:true}).waitFor();
 await page.getByRole('link',{name:'Create an account'}).click();
 await page.getByRole('heading',{name:'Create an account'}).waitFor();
 await page.screenshot({path:'artifacts/ui-review/signup-desktop.png',fullPage:true});
 await page.goto('http://127.0.0.1:4173/login');
 await page.getByTestId('theme-button').click(); await page.getByTestId('dark-mode').click(); await page.getByRole('menu').waitFor({state:'hidden'}); await page.waitForTimeout(250);
 await page.screenshot({path:'artifacts/ui-review/login-dark.png',fullPage:true});
 await page.getByTestId('theme-button').click(); await page.getByTestId('light-mode').click();
 await page.setViewportSize({width:390,height:844});
 await page.screenshot({path:'artifacts/ui-review/login-mobile.png',fullPage:true});
 if(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth)) throw new Error('Login horizontal overflow');
 await page.route('**/api/v1/users/me',route=>route.fulfill({json:{id:'preview-user',email:'preview@example.in',full_name:'Preview account',is_active:true,is_superuser:false}}));
 await page.evaluate(()=>localStorage.setItem('access_token','local-design-preview'));
 await page.setViewportSize({width:1440,height:1000});
 await page.goto('http://127.0.0.1:4173/');
 await page.getByRole('heading',{name:'Welcome, Preview.'}).waitFor();
 await page.screenshot({path:'artifacts/ui-review/overview-desktop.png',fullPage:true});
 await page.getByRole('link',{name:'Make it yours'}).click();
 await page.getByRole('heading',{name:'User Settings'}).waitFor({timeout:5000}).catch(()=>{});
 if(!page.url().endsWith('/settings')) throw new Error('Settings link failed');
 await page.goto('http://127.0.0.1:4173/');
 await page.setViewportSize({width:390,height:844});
 await page.getByRole('heading',{name:'Welcome, Preview.'}).waitFor(); await page.waitForTimeout(200);
 await page.screenshot({path:'artifacts/ui-review/overview-mobile.png',fullPage:true});
 if(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth)) throw new Error('Overview horizontal overflow');
 console.log(JSON.stringify({errors,checks:['login validation','signup navigation','theme switching','settings navigation','mobile overflow'],screenshots:6}));
 await browser.close();
 if(errors.length) process.exitCode=1;
})();




