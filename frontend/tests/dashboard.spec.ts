import {test,expect} from '@playwright/test';
test.beforeEach(async({page})=>{await page.goto('/');await expect(page.getByRole('heading',{name:'Metro Manila heat exposure'})).toBeVisible();});
test('real dataset, filters, and location detail',async({page})=>{
  await expect(page.getByText('Historical Reanalysis / PSA Census')).toBeVisible();
  await page.getByLabel('Location',{exact:true}).selectOption({label:'Makati'});
  await page.getByRole('button',{name:/01 Makati/}).click();
  await expect(page.getByRole('dialog')).toContainText('Makati');
  await expect(page.getByRole('dialog')).toContainText('629.6K');
  await page.getByLabel('Close detail panel').click();
  await page.getByLabel('Date',{exact:true}).fill('1900-01-01');
  await expect(page.getByText('No data available for the selected period.')).toBeVisible();
});
test('scenario changes and reset; unsupported environmental controls disabled',async({page})=>{
  await page.getByRole('button',{name:'Simulator LAB',exact:true}).click();
  const baseline=Number(await page.getByTestId('scenario-score').textContent());
  await expect(page.getByLabel('Vegetation increase',{exact:true})).toBeDisabled();
  await expect(page.getByLabel('Urban built-up intensity')).toBeDisabled();
  await page.getByLabel('Temperature change',{exact:true}).press('End');
  await expect.poll(async()=>Number(await page.getByTestId('scenario-score').textContent())).toBeGreaterThan(baseline);
  await page.getByRole('button',{name:'Reset scenario'}).click();
  await expect(page.getByTestId('scenario-score')).toHaveText(baseline.toFixed(1));
});
test('data explorer filtering and CSV export',async({page})=>{
  await page.getByRole('button',{name:'Data Explorer',exact:true}).click();
  await page.getByLabel('Search cities').fill('Quezon');
  await expect(page.locator('tbody tr')).toHaveCount(24);
  await expect(page.locator('tbody tr').first()).toContainText('Quezon City');
  const download=page.waitForEvent('download');
  await page.getByRole('button',{name:'Export CSV'}).click();
  expect((await download).suggestedFilename()).toBe('silong-filtered-reanalysis.csv');
});
test('forecast, methodology, source registry, and theme',async({page})=>{
  await page.getByRole('button',{name:'Forecast',exact:true}).click();
  await expect(page.getByRole('heading',{name:'Forecast trajectory'})).toBeVisible();
  await expect(page.getByText('No trained model is available.')).toHaveCount(0);
  await page.getByRole('button',{name:'Methodology',exact:true}).click();
  await expect(page.getByRole('heading',{name:'Every number has a source.'})).toBeVisible();
  await page.getByRole('button',{name:'Data Sources',exact:true}).click();
  await expect(page.getByRole('link',{name:'Download real dataset'})).toHaveAttribute('href','/data/era5-land-2025.csv');
  await page.getByLabel('Toggle dark mode').click();
  await expect(page.locator('html')).toHaveClass('dark');
  await page.reload();
  await expect(page.locator('html')).toHaveClass('dark');
});
test('mobile navigation and no horizontal viewport overflow',async({page})=>{
  await page.setViewportSize({width:390,height:844});
  await page.getByLabel('Toggle navigation').click();
  await page.getByRole('button',{name:'City Comparison',exact:true}).click();
  await expect(page.getByRole('heading',{name:'Choose up to four locations'})).toBeVisible();
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth)).toBeTruthy();
});
