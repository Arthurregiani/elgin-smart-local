mod bridge;
mod color;
mod wheel;
use color::{Light, hex, hsv_rgb, parse_hex, rgb_hsv};
use cosmic::{
    app::{Settings, Task},
    iced::{Length, Size, Subscription},
    prelude::*,
    widget,
};
use serde::{Deserialize, Serialize};
use serde_json::{Value, json};
use std::{collections::HashMap, path::PathBuf};

#[derive(Debug, Clone)]
pub enum Message {
    Event(Value),
    HelperEnded,
    Select(usize, bool),
    All,
    Value(&'static str, f32),
    Mode(String),
    Power(bool),
    Refresh,
    Edit(&'static str, String),
    Commit(&'static str),
    HexEdit(String),
    RgbEdit(usize, String),
    ApplyHex,
    ApplyRgb,
    PresetName(String),
    SavePreset,
    ApplyPreset(usize),
    DeletePreset(usize),
    Close,
    SmokeTick,
    Resize(Size),
    Screenshot(cosmic::iced::window::Screenshot),
}
struct Device {
    name: String,
    ip: String,
    version: String,
    selected: bool,
    state: Option<Light>,
    actual: Option<Light>,
    status: String,
    pending: u64,
}
#[derive(Clone, Serialize, Deserialize)]
struct Preset {
    name: String,
    light: Light,
}
struct App {
    core: cosmic::Core,
    bridge: Option<bridge::Bridge>,
    devices: Vec<Device>,
    seq: u64,
    notice: String,
    drafts: HashMap<&'static str, String>,
    hex_input: String,
    color_dirty: bool,
    rgb_input: [String; 3],
    presets: Vec<Preset>,
    preset_name: String,
    config: PathBuf,
    width: f32,
    smoke_tick: u32,
    smoke: bool,
}
fn base() -> PathBuf {
    std::env::var_os("ELGIN_HOME")
        .map(PathBuf::from)
        .unwrap_or_else(|| {
            PathBuf::from(env!("CARGO_MANIFEST_DIR"))
                .parent()
                .unwrap()
                .to_path_buf()
        })
}
#[derive(Clone, Debug)]
struct Flags;
impl cosmic::app::CosmicFlags for Flags {
    type SubCommand = String;
    type Args = Vec<String>;
}
fn main() -> cosmic::iced::Result {
    // Limit runtime worker count for a three-device desktop controller.
    unsafe {
        std::env::set_var("TOKIO_WORKER_THREADS", "2");
    }
    cosmic::app::run_single_instance::<App>(Settings::default().size(Size::new(1080., 840.)), Flags)
}
impl cosmic::Application for App {
    type Executor = cosmic::executor::Default;
    type Flags = Flags;
    type Message = Message;
    const APP_ID: &'static str = "io.github.elgin.SmartLocal";
    fn core(&self) -> &cosmic::Core {
        &self.core
    }
    fn core_mut(&mut self) -> &mut cosmic::Core {
        &mut self.core
    }
    fn init(core: cosmic::Core, _: Flags) -> (Self, Task<Message>) {
        let config = std::env::var_os("XDG_CONFIG_HOME")
            .map(PathBuf::from)
            .unwrap_or_else(|| PathBuf::from(std::env::var_os("HOME").unwrap()).join(".config"))
            .join("elgin-smart-local/presets.json");
        let presets = std::fs::read(&config)
            .ok()
            .and_then(|b| serde_json::from_slice(&b).ok())
            .unwrap_or_default();
        let result = bridge::Bridge::start(&base());
        let notice = result
            .as_ref()
            .err()
            .cloned()
            .unwrap_or_else(|| "Conectando às lâmpadas…".into());
        let mut app = Self {
            core,
            bridge: result.ok(),
            devices: vec![],
            seq: 0,
            notice,
            drafts: HashMap::new(),
            hex_input: String::new(),
            color_dirty: false,
            rgb_input: Default::default(),
            presets,
            preset_name: String::new(),
            config,
            width: 1080.,
            smoke_tick: 0,
            smoke: std::env::var_os("ELGIN_SMOKE").is_some(),
        };
        app.core.window.header_title = "Elgin Smart Local".into();
        let task = if let Some(id) = app.core.main_window_id() {
            app.set_window_title("Elgin Smart Local".into(), id)
        } else {
            Task::none()
        };
        (app, task)
    }
    fn subscription(&self) -> Subscription<Message> {
        let mut subs = vec![
            bridge::subscription(),
            cosmic::iced::window::resize_events().map(|(_, s)| Message::Resize(s)),
        ];
        if self.smoke {
            subs.push(
                cosmic::iced::time::every(std::time::Duration::from_secs(1))
                    .map(|_| Message::SmokeTick),
            );
        }
        Subscription::batch(subs)
    }
    fn on_close_requested(&self, _: cosmic::iced::window::Id) -> Option<Message> {
        Some(Message::Close)
    }
    fn update(&mut self, message: Message) -> Task<Message> {
        match message {
            Message::Resize(s) => self.width = s.width,
            Message::SmokeTick => {
                self.smoke_tick += 1;
                if self.smoke_tick == 5 {
                    for (i, d) in self.devices.iter_mut().enumerate() {
                        d.selected = i == 2;
                    }
                    self.reset_inputs();
                }
                if let Some(id) = self.core.main_window_id() {
                    if [3, 7, 11].contains(&self.smoke_tick) {
                        return cosmic::iced::window::screenshot(id)
                            .map(|s| cosmic::Action::App(Message::Screenshot(s)));
                    }
                    if self.smoke_tick == 9 {
                        return cosmic::iced::window::resize(id, Size::new(620., 860.));
                    }
                }
                if self.smoke_tick >= 13 {
                    self.bridge.take();
                    return cosmic::iced::exit();
                }
            }
            Message::Screenshot(s) => {
                let path = base().join(format!("evidence/ui-{}.png", self.smoke_tick));
                let _ = image::save_buffer(
                    path,
                    &s.rgba,
                    s.size.width,
                    s.size.height,
                    image::ColorType::Rgba8,
                );
            }
            Message::Close => {
                self.bridge.take();
                return cosmic::iced::exit();
            }
            Message::HelperEnded => {
                self.notice = "Comunicação encerrada. Reabra o aplicativo para reconectar.".into();
                for d in &mut self.devices {
                    d.status = "Desconectada".into();
                }
            }
            Message::Event(v) => self.event(v),
            Message::Select(i, b) => {
                if let Some(d) = self.devices.get_mut(i) {
                    d.selected = b
                }
                self.reset_inputs();
            }
            Message::All => {
                let select = !self.devices.iter().all(|d| d.selected);
                for d in &mut self.devices {
                    d.selected = select
                }
                self.reset_inputs();
            }
            Message::Value(k, n) => {
                let n = n.round() as u16;
                self.drafts.remove(k);
                self.change(json!({k:n}));
            }
            Message::Mode(m) => self.change(json!({"mode":m})),
            Message::Power(b) => self.change(json!({"on":b})),
            Message::Refresh => {
                for (i, d) in self.devices.iter_mut().enumerate() {
                    if d.selected {
                        d.status = "Lendo estado…".into();
                        if let Some(b) = &self.bridge {
                            b.send(json!({"op":"refresh","index":i}));
                        }
                    }
                }
            }
            Message::Edit(k, s) => {
                self.drafts.insert(k, s);
            }
            Message::Commit(k) => {
                if let Some(s) = self.drafts.get(k).cloned() {
                    let n = s.replace(',', ".").parse::<f32>();
                    let max = if k == "h" { 360. } else { 100. };
                    match n {
                        Ok(n) if n.is_finite() && (0. ..=max).contains(&n) => {
                            self.drafts.remove(k);
                            self.change(json!({k:(n*if k=="h"{1.}else{10.}).round() as u16}));
                        }
                        _ => {
                            self.notice = format!("Informe um valor de 0 a {max}; Enter confirma.")
                        }
                    }
                }
            }
            Message::HexEdit(s) => {
                self.hex_input = s;
                self.color_dirty = true;
            }
            Message::RgbEdit(i, s) => {
                self.rgb_input[i] = s;
                self.color_dirty = true;
            }
            Message::ApplyHex => {
                if let Some(rgb) = parse_hex(&self.hex_input) {
                    self.apply_rgb(rgb)
                } else {
                    self.notice = "Use hexadecimal com seis dígitos, por exemplo #FFD4A8.".into()
                }
            }
            Message::ApplyRgb => {
                let rgb: Option<Vec<u8>> = self
                    .rgb_input
                    .iter()
                    .map(|s| s.trim().parse().ok())
                    .collect();
                if let Some(rgb) = rgb {
                    self.apply_rgb([rgb[0], rgb[1], rgb[2]])
                } else {
                    self.notice = "Cada canal RGB deve ser um inteiro entre 0 e 255.".into()
                }
            }
            Message::PresetName(s) => self.preset_name = s,
            Message::SavePreset => {
                if let Some(light) = self.reference().cloned() {
                    if self.preset_name.trim().is_empty() {
                        self.notice = "Dê um nome ao preset.".into()
                    } else {
                        let p = Preset {
                            name: self.preset_name.trim().chars().take(64).collect(),
                            light,
                        };
                        if let Some(old) = self.presets.iter_mut().find(|x| x.name == p.name) {
                            *old = p
                        } else {
                            self.presets.push(p)
                        }
                        self.save_presets();
                        self.preset_name.clear();
                    }
                }
            }
            Message::ApplyPreset(i) => {
                if let Some(p) = self.presets.get(i) {
                    let mut v = serde_json::to_value(&p.light).unwrap();
                    v.as_object_mut().unwrap().remove("on");
                    self.change(v);
                }
            }
            Message::DeletePreset(i) => {
                if i < self.presets.len() {
                    self.presets.remove(i);
                    self.save_presets();
                }
            }
        }
        Task::none()
    }
    fn view(&self) -> Element<'_, Message> {
        let mut lamps = widget::column::with_capacity(8)
            .spacing(12)
            .push(widget::text::title3("Suas lâmpadas"));
        for (i, d) in self.devices.iter().enumerate() {
            lamps = lamps
                .push(
                    widget::checkbox(d.selected)
                        .label(d.name.clone())
                        .on_toggle(move |b| Message::Select(i, b)),
                )
                .push(widget::text::caption(format!(
                    "{} · Tuya {}",
                    d.ip, d.version
                )))
                .push(widget::text::body(d.status.clone()));
            if let Some(a) = &d.actual {
                lamps = lamps.push(widget::text::caption(format!(
                    "{} · {} · H {}° / S {:.1}% / V {:.1}%\nBranco {:.1}% · Temperatura {:.1}%",
                    if a.on { "Ligada" } else { "Desligada" },
                    match a.mode.as_str() {
                        "white" => "branco",
                        "colour" => "colorido",
                        _ => a.mode.as_str(),
                    },
                    a.h,
                    a.s as f32 / 10.,
                    a.v as f32 / 10.,
                    a.white as f32 / 10.,
                    a.temperature as f32 / 10.
                )));
            }
            lamps = lamps.push(widget::divider::horizontal::default());
        }
        lamps = lamps
            .push(widget::button::standard("Selecionar / desmarcar todas").on_press(Message::All))
            .push(widget::button::standard("Sincronizar estado real").on_press(Message::Refresh));
        let mut body = widget::column::with_capacity(8)
            .spacing(10)
            .push(widget::text::title2("Luz, com precisão."))
            .push(widget::text::body(
                "Controle local • ajustes independentes • sem nuvem",
            ));
        body = body.push(widget::text::body(self.notice.clone()));
        if let Some(s) = self.reference() {
            let selected = self.devices.iter().filter(|d| d.selected).count();
            let name = &self
                .devices
                .iter()
                .find(|d| d.selected && d.state.is_some())
                .unwrap()
                .name;
            let mut controls = widget::column::with_capacity(8)
                .spacing(14)
                .push(widget::text::title3(if selected > 1 {
                    format!("{selected} lâmpadas selecionadas")
                } else {
                    name.clone()
                }))
                .push(
                    widget::row::with_capacity(4)
                        .spacing(8)
                        .push(widget::button::suggested("Ligar").on_press(Message::Power(true)))
                        .push(widget::button::standard("Desligar").on_press(Message::Power(false))),
                )
                .push(
                    widget::row::with_capacity(4)
                        .spacing(8)
                        .push(
                            widget::button::standard(if s.mode == "colour" {
                                "● Colorido"
                            } else {
                                "Colorido"
                            })
                            .on_press(Message::Mode("colour".into())),
                        )
                        .push(
                            widget::button::standard(if s.mode == "white" {
                                "● Branco"
                            } else {
                                "Branco"
                            })
                            .on_press(Message::Mode("white".into())),
                        ),
                );
            if selected > 1 {
                controls=controls.push(widget::text::caption(format!("Valores exibidos: {name}. Cada ajuste preserva os outros componentes de cada lâmpada.")));
            }
            if s.mode == "colour" {
                let wheel = widget::Canvas::new(wheel::Wheel {
                    h: s.h,
                    s: s.s,
                    v: s.v,
                })
                .width(Length::Fixed(210.))
                .height(Length::Fixed(210.));
                let adjustments = widget::column::with_capacity(4)
                    .spacing(14)
                    .push(self.slider("Brilho da cor", "v", s.v, 1000))
                    .push(self.slider("Saturação", "s", s.s, 1000))
                    .push(self.slider("Tonalidade (Hue)", "h", s.h, 360));
                controls = if self.width < 900. {
                    controls.push(wheel).push(adjustments)
                } else {
                    controls.push(
                        widget::row::with_capacity(2)
                            .spacing(16)
                            .push(wheel)
                            .push(adjustments.width(Length::Fill)),
                    )
                };
                controls = controls
                    .push(widget::text::caption(
                        "Anel: altera só Hue. Centro: prévia RGB. S e V são preservados.",
                    ))
                    .push(widget::text::caption(format!(
                        "HSV nativo: {} / {} / {} · {}",
                        s.h,
                        s.s,
                        s.v,
                        hex(hsv_rgb(s.h, s.s, s.v))
                    )))
                    .push(
                        widget::row::with_capacity(4)
                            .spacing(8)
                            .push(
                                widget::text_input("#RRGGBB", &self.hex_input)
                                    .on_input(Message::HexEdit)
                                    .on_submit(|_| Message::ApplyHex),
                            )
                            .push(
                                widget::button::standard("Aplicar HEX").on_press(Message::ApplyHex),
                            ),
                    );
                let mut rgb = widget::row::with_capacity(4).spacing(8);
                for (i, l) in ["R: 0–255", "G: 0–255", "B: 0–255"].iter().enumerate() {
                    rgb = rgb.push(
                        widget::text_input(*l, &self.rgb_input[i])
                            .on_input(move |s| Message::RgbEdit(i, s))
                            .on_submit(|_| Message::ApplyRgb),
                    );
                }
                controls=controls.push(rgb.push(widget::button::standard("Aplicar RGB").on_press(Message::ApplyRgb)))
     .push(widget::text::caption("HEX/RGB define H, S e V juntos. Para preservar S e V, use o anel ou Hue. V=0 é preto; o botão Desligar corta a emissão pelo DPS 20."));
            } else {
                if s.mode != "white" {
                    controls = controls.push(widget::text::body(
                        "Modo externo ativo. Selecione Branco ou Colorido para editar.",
                    ));
                } else {
                    controls = controls
                        .push(self.slider("Brilho branco", "white", s.white, 1000))
                        .push(widget::text::caption(
                            "0% desliga. Mínimo branco: 1,0% (DPS 22 = 10). Passo: 0,1%.",
                        ))
                        .push(self.slider(
                            "Temperatura • quente → frio",
                            "temperature",
                            s.temperature,
                            1000,
                        ))
                        .push(widget::text::caption(
                            "Escala nativa 0–1000. O dispositivo não informa calibração em kelvin.",
                        ));
                }
            }
            controls = controls
                .push(widget::divider::horizontal::default())
                .push(widget::text::title3("Seus presets"))
                .push(
                    widget::row::with_capacity(4)
                        .spacing(8)
                        .push(
                            widget::text_input("Nome do preset", &self.preset_name)
                                .on_input(Message::PresetName)
                                .on_submit(|_| Message::SavePreset),
                        )
                        .push(widget::button::standard("Salvar").on_press(Message::SavePreset)),
                );
            for (i, p) in self.presets.iter().enumerate() {
                controls = controls.push(
                    widget::row::with_capacity(4)
                        .spacing(8)
                        .push(
                            widget::button::standard(p.name.clone())
                                .on_press(Message::ApplyPreset(i)),
                        )
                        .push(widget::button::text("Remover").on_press(Message::DeletePreset(i))),
                );
            }
            controls=controls.push(widget::text::caption("Presets guardam os dois modos e preservam liga/desliga ao aplicar. Enter confirma os campos numéricos."));
            if self.width < 900. {
                body = body.push(lamps).push(controls)
            } else {
                body = body.push(
                    widget::row::with_capacity(4)
                        .spacing(28)
                        .push(lamps.width(Length::Fixed(290.)))
                        .push(controls.width(Length::Fill)),
                );
            }
        } else {
            body = body.push(lamps).push(widget::text::body(
                "Selecione uma lâmpada conectada para ajustar a iluminação.",
            ));
        }
        widget::container(widget::scrollable(body))
            .padding(24)
            .width(Length::Fill)
            .height(Length::Fill)
            .into()
    }
}
impl App {
    fn reference(&self) -> Option<&Light> {
        self.devices
            .iter()
            .filter(|d| d.selected)
            .find_map(|d| d.state.as_ref())
    }
    fn reset_inputs(&mut self) {
        self.drafts.clear();
        self.color_dirty = false;
        self.sync_color_inputs();
    }
    fn sync_color_inputs(&mut self) {
        if let Some(s) = self.reference() {
            let rgb = hsv_rgb(s.h, s.s, s.v);
            self.hex_input = hex(rgb);
            self.rgb_input = rgb.map(|x| x.to_string());
        }
    }
    fn slider(
        &self,
        label: &'static str,
        k: &'static str,
        n: u16,
        max: u16,
    ) -> Element<'_, Message> {
        let value = self.drafts.get(k).cloned().unwrap_or_else(|| {
            if k == "h" {
                n.to_string()
            } else {
                format!("{:.1}", n as f32 / 10.)
            }
        });
        widget::column::with_capacity(8)
            .spacing(6)
            .push(widget::text::body(label))
            .push(
                widget::row::with_capacity(4)
                    .spacing(12)
                    .push(
                        widget::slider(0. ..=max as f32, n as f32, move |v| Message::Value(k, v))
                            .step(1_f32),
                    )
                    .push(
                        widget::text_input(if k == "h" { "graus" } else { "%" }, value)
                            .on_input(move |s| Message::Edit(k, s))
                            .on_submit(move |_| Message::Commit(k))
                            .width(Length::Fixed(90.)),
                    ),
            )
            .into()
    }
    fn change(&mut self, patch: Value) {
        if self.smoke {
            return;
        }
        let Some(b) = &self.bridge else { return };
        let mut count = 0;
        for (i, d) in self
            .devices
            .iter_mut()
            .enumerate()
            .filter(|(_, d)| d.selected)
        {
            let Some(s) = &mut d.state else { continue };
            self.seq += 1;
            d.pending = self.seq;
            if !b.send(json!({"op":"set","index":i,"seq":self.seq,"patch":patch})) {
                self.notice = "Falha na comunicação local.".into();
                return;
            }
            let mut v = serde_json::to_value(&*s).unwrap();
            for (k, n) in patch.as_object().unwrap() {
                v[k] = n.clone();
            }
            if patch.get("white") == Some(&json!(0)) {
                v["white"] = json!(s.white);
                v["on"] = json!(false)
            } else if patch.get("white").is_some() {
                v["white"] = json!(v["white"].as_u64().unwrap().max(10));
            }
            if let Ok(new) = serde_json::from_value(v) {
                *s = new;
            }
            d.status = "Aguardando confirmação…".into();
            count += 1;
        }
        self.notice = if count > 0 {
            "Ajustando. O estado confirmado aparece junto a cada lâmpada.".into()
        } else {
            "Nenhuma lâmpada com estado conhecido selecionada.".into()
        };
    }
    fn apply_rgb(&mut self, rgb: [u8; 3]) {
        self.color_dirty = false;
        // Gray/black has no defined hue: preserve each target's own hue.
        let (h, s, v) = rgb_hsv(rgb, self.reference().map(|s| s.h).unwrap_or(0));
        let patch = if s == 0 {
            json!({"s":s,"v":v})
        } else {
            json!({"h":h,"s":s,"v":v})
        };
        self.change(patch);
    }
    fn event(&mut self, v: Value) {
        match v["event"].as_str().unwrap_or("") {
            "devices" => {
                self.devices = v["devices"]
                    .as_array()
                    .unwrap_or(&vec![])
                    .iter()
                    .enumerate()
                    .map(|(i, d)| Device {
                        name: d["name"].as_str().unwrap_or("Lâmpada").into(),
                        ip: d["ip"].as_str().unwrap_or("").into(),
                        version: d["version"].as_str().unwrap_or("").into(),
                        selected: i == 0,
                        state: None,
                        actual: None,
                        status: "Conectando…".into(),
                        pending: 0,
                    })
                    .collect();
            }
            "state" => {
                let i = v["index"].as_u64().unwrap_or(999) as usize;
                if let Some(d) = self.devices.get_mut(i)
                    && let Ok(s) = serde_json::from_value::<Light>(v["state"].clone())
                {
                    d.actual = Some(s.clone());
                    if v["seq"].as_u64().unwrap_or(0) >= d.pending {
                        d.state = Some(s);
                        d.status = if v["status"] == "divergent" {
                            format!("Divergência: {}", v["differences"])
                        } else {
                            "Sincronizada ✓".into()
                        };
                    }
                }
                if !self.color_dirty {
                    self.sync_color_inputs()
                }
                if self
                    .devices
                    .iter()
                    .all(|d| d.status.starts_with("Sincronizada"))
                {
                    self.notice = "Estado real confirmado. Pronto para ajustar.".into();
                }
            }
            "error" => {
                if let Some(d) = self
                    .devices
                    .get_mut(v["index"].as_u64().unwrap_or(999) as usize)
                    && v["seq"].as_u64().unwrap_or(0) >= d.pending
                {
                    d.status = v["message"].as_str().unwrap_or("Falha LAN").into();
                    self.notice="Uma lâmpada não confirmou o comando. O último estado lido continua visível.".into();
                }
            }
            "fatal" | "invalid" => {
                self.notice = v["message"]
                    .as_str()
                    .unwrap_or("Falha de comunicação")
                    .into()
            }
            _ => {}
        }
    }
    fn save_presets(&mut self) {
        use std::io::Write;
        use std::os::unix::fs::{OpenOptionsExt, PermissionsExt};
        let result = (|| -> std::io::Result<()> {
            let dir = self.config.parent().unwrap();
            std::fs::create_dir_all(dir)?;
            std::fs::set_permissions(dir, std::fs::Permissions::from_mode(0o700))?;
            let temp = self.config.with_extension("tmp");
            let mut f = std::fs::OpenOptions::new()
                .create(true)
                .truncate(true)
                .write(true)
                .mode(0o600)
                .open(&temp)?;
            f.write_all(serde_json::to_string_pretty(&self.presets)?.as_bytes())?;
            f.sync_all()?;
            std::fs::rename(temp, &self.config)
        })();
        self.notice = if result.is_ok() {
            "Presets salvos neste computador.".into()
        } else {
            "Não foi possível salvar os presets.".into()
        };
    }
}
