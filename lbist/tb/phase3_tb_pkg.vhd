library ieee;
use ieee.std_logic_1164.all;
package phase3_tb_pkg is
  type timing_t is record a,b,g : natural; end record;
  type nat_array is array(natural range <>) of natural;
  function schedule_period(app,l,b : natural) return positive;
  function reference_timing(app,l,b,p,c : natural; initial : natural := 0) return timing_t;
  function reference_mode(t : timing_t; position : natural) return std_logic_vector;
  function name_of(app : natural) return string;
end package;
package body phase3_tb_pkg is
  function schedule_period(app,l,b : natural) return positive is
  begin
    if app=3 then return 2; end if;
    if app=4 and b<=l then
      if l-b>=28 then return l-b-27; end if;
    end if;
    return 1;
  end;
  function reference_timing(app,l,b,p,c : natural; initial : natural := 0) return timing_t is
    variable t : timing_t := (0,b,0);
  begin
    if b>l then return t; end if;
    if app=2 then t.a:=(l-b)/2; t.g:=t.a;
    elsif app=3 then
      if b>l/2 then return t; end if;
      if (p+c) mod 2=0 then t.a:=l/2-b; t.g:=l/2;
      else t.a:=l/2; t.g:=l/2-b; end if;
    elsif app=4 then
      t.g:=14+(p+initial) mod schedule_period(app,l,b);
      if t.g<=l-b then t.a:=l-b-t.g; end if;
    else t.a:=0; t.g:=0; end if;
    return t;
  end;
  function reference_mode(t : timing_t; position : natural) return std_logic_vector is
  begin
    if position>=t.g and position<t.g+t.b then return "11"; end if;
    return "00";
  end;
  function name_of(app : natural) return string is
  begin
    case app is when 0=>return "direct"; when 1=>return "low";
      when 2=>return "basic"; when 3=>return "swap"; when others=>return "moving"; end case;
  end;
end package body;
