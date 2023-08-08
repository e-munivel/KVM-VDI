// @ts-check
const { test } = require('@playwright/test')
const { PageLogin } = require('./login-page')

test.describe('Login', () => {
  test('should login locally correctly against the DB', async ({ page }) => {
    const login = new PageLogin(page)
    await login.goto()
    await login.form('admin', 'IsardVDI')
    await login.finished()
  })
})
