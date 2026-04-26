import codecs
path = 'c:/tools/workspace/Agre_ERP_2027-main/frontend/src/components/Nav.jsx'
with codecs.open(path, 'r', 'utf-8') as f:
    text = f.read()

text = text.replace('isFinanceLeader', 'isFinancialRole')
text = text.replace('visible: ({ isAdmin, isSuperuser, strictErpMode }) => isAdmin || isSuperuser || strictErpMode,', 'visible: ({ isAdmin, isSuperuser, strictErpMode, hasFarmRole }) => isAdmin || isSuperuser || strictErpMode || isInventoryRole({ isSuperuser, hasFarmRole }),')
text = text.replace('visible: ({ isAdmin, isSuperuser, strictErpMode }) =>\n      Boolean(strictErpMode) && (isAdmin || isSuperuser),', 'visible: ({ isAdmin, isSuperuser, strictErpMode, hasFarmRole }) =>\n      (Boolean(strictErpMode) && (isAdmin || isSuperuser)) || isInventoryRole({ isSuperuser, hasFarmRole }),')
text = text.replace('visible: ({ isAdmin, isSuperuser, strictErpMode }) =>\r\n      Boolean(strictErpMode) && (isAdmin || isSuperuser),', 'visible: ({ isAdmin, isSuperuser, strictErpMode, hasFarmRole }) =>\n      (Boolean(strictErpMode) && (isAdmin || isSuperuser)) || isInventoryRole({ isSuperuser, hasFarmRole }),')
text = text.replace('visible: (ctx) => isFinancialRole(ctx) || ctx.isAdmin,', 'visible: (ctx) => isFinancialRole(ctx) || ctx.isAdmin || isSalesRole(ctx),')

with codecs.open(path, 'w', 'utf-8') as f:
    f.write(text)
print("Finished replacements")
