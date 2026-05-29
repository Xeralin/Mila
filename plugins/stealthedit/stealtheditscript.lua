function cbFindIntegrityCheckChange(sender)
  local enabled = checkbox_getState(frmSESettings_cbFindIntegrityCheck) == cbChecked
  control_setEnabled(frmSESettings_cbRewatch, enabled)
  control_setEnabled(frmSESettings_edtTime, enabled)
  control_setEnabled(frmSESettings_lblMilliseconds, enabled)
end

function btnApplyClick(sender)
  stealthedit_FindIntegrity = checkbox_getState(frmSESettings_cbFindIntegrityCheck) == cbChecked
  stealthedit_Rewatch = checkbox_getState(frmSESettings_cbRewatch) == cbChecked
  stealthedit_RewatchTimer = tonumber(control_getCaption(frmSESettings_edtTime))
end


createFormFromFile(stealtheditpath..'sesettings.FRM')
createFormFromFile(stealtheditpath..'results.FRM')


function ShowSEWindow()
  if stealthedit_FindIntegrity then
    form_show(frmResults)
  end
end

stealthedit_FindIntegrity = false
stealthedit_Rewatch = false
stealthedit_RewatchTimer = 100


function onreguard(sender)
  timer_setEnabled(sender, false)
  reguard()
end


se_events = {}

function IntegrityUpdate(rax, rbx, rcx, rdx, rsi, rdi, rbp, rsp, rip, r8, r9, r10, r11, r12, r13, r14, r15, stackcopy, stacksize)
  if not control_getVisible(frmResults) then
    ShowSEWindow()
  end

  if se_events[rip] == nil then
    se_events[rip] = {rax=rax, rbx=rbx, rcx=rcx, rdx=rdx, rsi=rsi, rdi=rdi, rbp=rbp, rsp=rsp, rip=rip, r8=r8, r9=r9, r10=r10, r11=r11, r12=r12, r13=r13, r14=r14, r15=r15, stackcopy=stackcopy, stacksize=stacksize}
    local items = listbox_getItems(frmResults_lbAddresses)
    strings_add(items, string.format('%08X', rip))

    if listbox_getItemIndex(frmResults_lbAddresses) == -1 then
      listbox_setItemIndex(frmResults_lbAddresses, 0)
    end
  end

  if stealthedit_Rewatch then
    if reguardtimer == nil then
      reguardtimer = createTimer(nil, false)
      timer_onTimer(reguardtimer, onreguard)
    end

    timer_setInterval(reguardtimer, stealthedit_RewatchTimer)
    timer_setEnabled(reguardtimer, true)
  end
end


function lbAddressesSelectionChange(sender, user)
  local is64bit = targetIs64Bit()
  local items = listbox_getItems(frmResults_lbAddresses)
  local itemindex = listbox_getItemIndex(frmResults_lbAddresses)
  local event = se_events[tonumber(strings_getString(items, itemindex), 16)]

  edit_clear(frmResults_mData)

  local prefix = is64bit and 'R' or 'E'

  for _, name in ipairs({'AX','BX','CX','DX','SI','DI','BP','SP','IP'}) do
    memo_append(frmResults_mData, string.format('%s%s = %08X', prefix, name, event['r'..name:lower()]))
  end

  if is64bit then
    for i = 8, 15 do
      memo_append(frmResults_mData, string.format('%3s = %08X', 'R'..i, event['r'..i]))
    end
  end

  memo_append(frmResults_mData, '')
  memo_append(frmResults_mData, string.format('Stack copy = %08X', event.stackcopy))
  memo_append(frmResults_mData, string.format('Stack size = %08X', event.stacksize))
end

function lbAddressesDblClick(sender)
  local items = listbox_getItems(frmResults_lbAddresses)
  local itemindex = listbox_getItemIndex(frmResults_lbAddresses)
  local address = tonumber(strings_getString(items, itemindex), 16)
  local mb = getMemoryViewForm()
  local dv = memoryview_getDisassemblerView(mb)
  disassemblerview_setSelectedAddress(dv, address)
  form_show(mb)
end

function stealthedit_adjustRegionCopy(originaladdress, newaddress, size)
  local rrs = createRipRelativeScanner(newaddress, newaddress+size, true)
  local diff = newaddress-originaladdress

  for i = 0, rrs.count-1 do
    writeInteger(rrs.Address[i], readInteger(rrs.Address[i])-diff)
  end

  rrs.destroy()

  if stealthedit_OnPostAdjustmentRegionCopy ~= nil then
    stealthedit_OnPostAdjustmentRegionCopy(originaladdress, newaddress, size)
  end
end

function stealthedit_allocMemoryForRegionCopy(baseaddress, size)
  if size == nil then return end

  autoAssemble([[
    alloc(secopy,]]..size..[[,"]]..string.format("%x", baseaddress)..[[")
    registersymbol(secopy)
  ]])

  local result = getAddress("secopy")
  unregisterSymbol("secopy")

  return result
end


function stealthedit_adjustModuleCopy64(modulename, newcopy)
  local originalbase = getAddress(modulename)
  local rrs = createRipRelativeScanner(modulename)
  local diff = newcopy-originalbase

  for i = 0, rrs.count-1 do
    writeInteger(rrs.Address[i]+diff, readInteger(rrs.Address[i])-diff)
  end

  rrs.destroy()

  if stealthedit_OnPostAdjustmentModuleCopy ~= nil then
    stealthedit_OnPostAdjustmentModuleCopy(modulename, newcopy)
  end
end

function stealthedit_allocMemoryForModuleCopy(modulename, size)
  if size == nil then
    size = getModuleSize(modulename)
  end

  autoAssemble([[
    alloc(secopy,]]..size..[[,"]]..modulename..[[")
    registersymbol(secopy)
  ]])

  local result = getAddress("secopy")
  unregisterSymbol("secopy")

  return result
end

function stealthedit_copymodulefor64bit(modulename)
  local originaladdress = getAddress(modulename)
  local copyaddress = stealthedit_allocMemoryForModuleCopy(modulename)

  local copy = readBytes(originaladdress, getModuleSize(modulename), true)
  writeBytes(copyaddress, copy)

  stealthedit_adjustModuleCopy64(modulename, copyaddress)

  return copyaddress
end
