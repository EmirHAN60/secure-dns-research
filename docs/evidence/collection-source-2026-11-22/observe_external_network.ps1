param([Parameter(Mandatory=$true)][string]$OutPath,[Parameter(Mandatory=$true)][string]$KeyPath,[string]$ObservationPhase='unspecified')
$ErrorActionPreference='Stop'
$key=[IO.File]::ReadAllBytes($KeyPath)
function Get-Tag([string]$Text) {
  $h=[Security.Cryptography.HMACSHA256]::new();$h.Key=$key
  try { return [Convert]::ToHexString($h.ComputeHash([Text.Encoding]::UTF8.GetBytes($Text))).ToLowerInvariant() }
  finally { $h.Dispose() }
}
$adapters=@([Net.NetworkInformation.NetworkInterface]::GetAllNetworkInterfaces() | Where-Object { $_.OperationalStatus -eq 'Up' -and $_.NetworkInterfaceType -ne 'Loopback' })
$candidates=@()
foreach($nic in $adapters) {
  $properties=$nic.GetIPProperties()
  $ipv4=@($properties.UnicastAddresses | Where-Object { $_.Address.AddressFamily -eq 'InterNetwork' })
  if($ipv4.Count -eq 0) { continue }
  $gateways=@($properties.GatewayAddresses | Where-Object { -not $_.Address.Equals([Net.IPAddress]::Any) -and -not $_.Address.Equals([Net.IPAddress]::IPv6Any) } | ForEach-Object { $_.Address.ToString() } | Sort-Object)
  $descriptor=$nic.Id+'|'+($gateways -join ',')
  $candidates+= [ordered]@{ adapter_tag=(Get-Tag $descriptor); media_type=$nic.NetworkInterfaceType.ToString(); reported_link_mbps=[math]::Round($nic.Speed/1000000); virtual_or_tunnel_hint=($nic.Description -match 'virtual|hamachi|vpn|tap|tun'); configured_gateway_count=$gateways.Count }
}
$routes=@()
foreach($target in @('1.1.1.1','8.8.8.8')) {
  $socket=[Net.Sockets.Socket]::new([Net.Sockets.AddressFamily]::InterNetwork,[Net.Sockets.SocketType]::Dgram,[Net.Sockets.ProtocolType]::Udp)
  try {
    # UDP Connect selects a local route; no Send/SendTo call or DNS query occurs.
    $socket.Connect([Net.IPAddress]::Parse($target),53)
    $local=$socket.LocalEndPoint.Address
    $matches=@($adapters | Where-Object { @($_.GetIPProperties().UnicastAddresses | Where-Object { $_.Address.Equals($local) }).Count -gt 0 })
    if($matches.Count -eq 0) { throw 'No matching local adapter for selected route' }
    $nic=$matches[0];$properties=$nic.GetIPProperties()
    $gateways=@($properties.GatewayAddresses | ForEach-Object { $_.Address.ToString() } | Sort-Object)
    $descriptor=$nic.Id+'|'+$local.ToString()+'|'+($gateways -join ',')
    $routes+=[ordered]@{ target=$target; destination_port=53; configuration_tag=(Get-Tag $descriptor); media_type=$nic.NetworkInterfaceType.ToString(); reported_link_mbps=[math]::Round($nic.Speed/1000000); virtual_or_tunnel_hint=($nic.Description -match 'virtual|hamachi|vpn|tap|tun'); error=$null }
  } catch {
    $routes+=[ordered]@{ target=$target; destination_port=53; configuration_tag=$null; error=$_.Exception.Message }
  } finally { $socket.Dispose() }
}
$record=[ordered]@{ observed_utc=[DateTime]::UtcNow.ToString('o'); observation_phase=$ObservationPhase; method='Local .NET network-interface observation and UDP route selection without application payload'; identity_scope='HMAC of local adapter identifier, selected local IPv4 address and configured gateways, using an undistributed local key. Equal tags describe equal observed local configuration; they do not prove an unchanged Internet path or public egress.'; network_names_recorded=$false; private_ip_addresses_recorded=$false; mac_addresses_recorded=$false; public_ip_lookup_performed=$false; private_key_distributed=$false; active_adapter_candidates=$candidates; udp_route_observations=$routes }
$record | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $OutPath -Encoding utf8
Write-Output ('Saved privacy-limited network observation: '+$ObservationPhase)
