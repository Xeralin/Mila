import QtQuick
import QtQuick.Controls.Basic
import ".."

Button {
    id: control

    property string variant: "secondary"
    property bool destructive: false

    readonly property bool _red: hovered || down

    readonly property color _grad_clear: Qt.alpha(Theme.accent, 0)
    readonly property color _grad_mid: Qt.alpha(Qt.darker(Theme.accent, down ? 2.2 : 2.0), 0.85)
    readonly property color _grad_bot: down ? Theme.accent_pressed : Qt.darker(Theme.accent, 1.2)

    readonly property color _label: {
        if (_red)
            return Theme.text_primary
        if (variant === "ghost")
            return destructive ? Theme.error : Theme.text_secondary
        return Theme.text_primary
    }

    property string neighbors: "horizontal"

    readonly property color _border_color: visualFocus || _red ? Theme.accent : Theme.button_border
    readonly property real _grow_x: neighbors === "horizontal" ? 12 : 6
    readonly property real _grow_y: neighbors === "vertical" ? 12 : 6
    readonly property real _cap_x: neighbors === "horizontal" ? 1 : 0.1
    readonly property real _cap_y: neighbors === "vertical" ? 1 : 0.1
    readonly property real _scale_x: {
        if (!control._red)
            return 1.0
        if (control.neighbors === "none")
            return 1.05
        return 1 + Math.min(control._grow_x / control.width, control._cap_x)
    }
    readonly property real _scale_y: {
        if (!control._red)
            return 1.0
        if (control.neighbors === "none")
            return 1.05
        return 1 + Math.min(control._grow_y / control.height, control._cap_y)
    }

    implicitHeight: Theme.control_height
    leftPadding: 18
    rightPadding: 18
    topPadding: 0
    bottomPadding: 0
    hoverEnabled: true
    opacity: enabled ? 1.0 : 0.4
    font.pixelSize: Theme.font_small
    font.bold: true
    font.capitalization: Font.AllUppercase
    font.letterSpacing: 1.2

    background: Rectangle {
        implicitWidth: 80
        implicitHeight: Theme.control_height
        radius: Theme.radius_small
        color: control._red ? Theme.button_fill_solid : (control.variant === "ghost" ? "transparent" : Theme.button_fill)

        transform: Scale {
            origin.x: control.width / 2
            origin.y: control.height / 2
            xScale: control._scale_x
            yScale: control._scale_y

            Behavior on xScale { NumberAnimation { duration: 60; easing.type: Easing.Linear } }
            Behavior on yScale { NumberAnimation { duration: 60; easing.type: Easing.Linear } }
        }

        Rectangle {
            anchors.fill: parent
            radius: Theme.radius_small
            visible: control._red
            gradient: Gradient {
                GradientStop {
                    position: 0.0
                    color: control._grad_clear
                }
                GradientStop {
                    position: 0.35
                    color: control._grad_clear
                }
                GradientStop {
                    position: 0.85
                    color: control._grad_mid
                }
                GradientStop {
                    position: 1.0
                    color: control._grad_bot
                }
            }
        }

        Rectangle {
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.bottom: parent.bottom
            height: 4
            color: Theme.accent
            visible: control._red
        }

        Rectangle {
            anchors.top: parent.top
            width: parent.width
            height: 1
            color: control._border_color
        }

        Rectangle {
            anchors.bottom: parent.bottom
            width: parent.width
            height: 1
            color: control._border_color
        }

        Rectangle {
            anchors.left: parent.left
            width: 1
            height: parent.height
            color: control._border_color
        }

        Rectangle {
            anchors.right: parent.right
            width: 1
            height: parent.height
            color: control._border_color
        }
    }

    contentItem: Text {
        text: control.text
        font: control.font
        color: control._label
        horizontalAlignment: Text.AlignHCenter
        verticalAlignment: Text.AlignVCenter
        elide: Text.ElideRight
    }
}
