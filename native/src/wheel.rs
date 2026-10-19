use crate::{Message, color::hsv_rgb};
use cosmic::{
    Renderer, Theme,
    iced::{self, Color, Point, Rectangle, mouse},
    widget::canvas::{self, Frame, Geometry, Path, Stroke},
};
#[derive(Default)]
pub struct WheelState {
    drag: bool,
}
pub struct Wheel {
    pub h: u16,
    pub s: u16,
    pub v: u16,
}
impl canvas::Program<Message, Theme, Renderer> for Wheel {
    type State = WheelState;
    fn update(
        &self,
        state: &mut WheelState,
        event: &canvas::Event,
        bounds: Rectangle,
        cursor: mouse::Cursor,
    ) -> Option<iced::widget::Action<Message>> {
        match event {
            canvas::Event::Mouse(mouse::Event::ButtonPressed(mouse::Button::Left)) => {
                let p = cursor.position_in(bounds)?;
                let c = Point::new(bounds.width / 2., bounds.height / 2.);
                let r = bounds.width.min(bounds.height) / 2. - 10.;
                let d = p.distance(c);
                state.drag = d >= r - 28. && d <= r;
            }
            canvas::Event::Mouse(mouse::Event::ButtonReleased(mouse::Button::Left)) => {
                state.drag = false;
                return None;
            }
            canvas::Event::Mouse(mouse::Event::CursorMoved { .. }) => {}
            _ => return None,
        }
        if state.drag {
            let p = cursor.position_in(bounds)?;
            let h = (p.y - bounds.height / 2.)
                .atan2(p.x - bounds.width / 2.)
                .to_degrees()
                .rem_euclid(360.)
                .round() as u16;
            return Some(
                iced::widget::Action::publish(Message::Value("h", h as f32)).and_capture(),
            );
        }
        None
    }
    fn draw(
        &self,
        _: &WheelState,
        renderer: &Renderer,
        _: &Theme,
        bounds: Rectangle,
        _: mouse::Cursor,
    ) -> Vec<Geometry<Renderer>> {
        let mut f = Frame::new(renderer, bounds.size());
        let c = Point::new(bounds.width / 2., bounds.height / 2.);
        let r = bounds.width.min(bounds.height) / 2. - 10.;
        for h in 0..360 {
            let a = (h as f32).to_radians();
            let b = (h as f32 + 1.5).to_radians();
            let p = Path::new(|p| {
                p.move_to(Point::new(
                    c.x + (r - 28.) * a.cos(),
                    c.y + (r - 28.) * a.sin(),
                ));
                p.line_to(Point::new(c.x + r * a.cos(), c.y + r * a.sin()));
                p.line_to(Point::new(c.x + r * b.cos(), c.y + r * b.sin()));
                p.line_to(Point::new(
                    c.x + (r - 28.) * b.cos(),
                    c.y + (r - 28.) * b.sin(),
                ));
                p.close();
            });
            let [rr, g, b] = hsv_rgb(h, 1000, 1000);
            f.fill(&p, Color::from_rgb8(rr, g, b));
        }
        let [r8, g, b] = hsv_rgb(self.h, self.s, self.v);
        f.fill(&Path::circle(c, r - 36.), Color::from_rgb8(r8, g, b));
        let a = (self.h as f32).to_radians();
        let marker = Point::new(c.x + (r - 14.) * a.cos(), c.y + (r - 14.) * a.sin());
        f.stroke(
            &Path::circle(marker, 9.),
            Stroke::default().with_color(Color::BLACK).with_width(5.),
        );
        f.stroke(
            &Path::circle(marker, 9.),
            Stroke::default().with_color(Color::WHITE).with_width(2.),
        );
        vec![f.into_geometry()]
    }
    fn mouse_interaction(
        &self,
        _: &WheelState,
        bounds: Rectangle,
        cursor: mouse::Cursor,
    ) -> mouse::Interaction {
        if cursor.is_over(bounds) {
            mouse::Interaction::Crosshair
        } else {
            mouse::Interaction::default()
        }
    }
}
